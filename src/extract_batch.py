import re
from pathlib import Path
import pandas as pd
import pdfplumber
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]
PDF_DIR = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = OUT_DIR / "run_log.txt"


def log(msg: str):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def grab1(pattern: str, text: str):
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def grab_last_number(pattern: str, text: str):
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None
    return m.groups()[-1].strip()


def clean_amount(x):
    if x is None:
        return None
    x = str(x).strip()
    if not x or x.lower() in {"na", "nan", "-"}:
        return None
    x = x.replace(",", "")
    x = re.sub(r"[^\d\.\-]", "", x)
    if x in {"", "-", "."}:
        return None
    try:
        return float(x)
    except ValueError:
        return None


def extract_account_info(pdf_path: Path) -> dict:
    text = ""
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages[:2]:
            text += "\n" + (page.extract_text() or "")

    info = {
        "pdf_file": pdf_path.name,
        "account_number": grab1(r"Account\s+Number\s*[:\-]?\s*(\d+)", text),
        "holder_name": grab1(r"Account\s+Holder\s+Name\s*[:\-]?\s*(.+)", text),
        "customer_id": grab_last_number(r"(Customer\s*ID|CIF)\s*[:\-]?\s*(\d+)", text),
        "ifsc_code": grab1(r"IFSC\s+Code\s*[:\-]?\s*([A-Z0-9]+)", text),
        "branch": grab1(r"Branch\s*[:\-]?\s*(.+)", text),
    }

    m = re.search(
        r"Statement\s+Period\s*[:\-]?\s*([0-9A-Za-z\-]+)\s*to\s*([0-9A-Za-z\-]+)",
        text,
        re.IGNORECASE,
    )
    info["period_from"] = m.group(1).strip() if m else None
    info["period_to"] = m.group(2).strip() if m else None

    if info["branch"]:
        info["branch"] = info["branch"].split("Statement")[0].strip()
    if info["holder_name"]:
        info["holder_name"] = info["holder_name"].split("Customer")[0].strip()

    return info


def extract_transactions(pdf_path: Path) -> pd.DataFrame:
    all_rows = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables() or []
            for tbl in tables:
                if not tbl or len(tbl) < 2:
                    continue

                header_idx = None
                for i, row in enumerate(tbl[:5]):
                    joined = " ".join([str(c or "") for c in row]).lower()
                    if ("date" in joined and "narration" in joined and "balance" in joined):
                        header_idx = i
                        break
                if header_idx is None:
                    continue

                headers = [str(h or "").strip().lower() for h in tbl[header_idx]]
                headers = [re.sub(r"\s+", " ", h).replace("transaction type", "type") for h in headers]

                for row in tbl[header_idx + 1:]:
                    if not row or all((c is None or str(c).strip() == "") for c in row):
                        continue
                    rec = {}
                    for j in range(max(len(headers), len(row))):
                        key = headers[j] if j < len(headers) else f"col{j}"
                        val = row[j] if j < len(row) else None
                        rec[key] = val
                    all_rows.append(rec)

    df = pd.DataFrame(all_rows)
    if df.empty:
        return df

    rename_map = {}
    for c in df.columns:
        cl = c.lower()
        if cl.startswith("date"):
            rename_map[c] = "txn_date"
        elif "narration" in cl or "description" in cl:
            rename_map[c] = "narration"
        elif "reference" in cl or cl == "ref":
            rename_map[c] = "reference"
        elif "type" in cl:
            rename_map[c] = "dr_cr"
        elif "debit" in cl:
            rename_map[c] = "debit"
        elif "credit" in cl:
            rename_map[c] = "credit"
        elif "balance" in cl:
            rename_map[c] = "balance"

    df = df.rename(columns=rename_map)
    keep = [c for c in ["txn_date", "narration", "reference", "dr_cr", "debit", "credit", "balance"] if c in df.columns]
    df = df[keep].copy()

    if "debit" in df.columns:
        df["debit"] = df["debit"].apply(clean_amount)
    if "credit" in df.columns:
        df["credit"] = df["credit"].apply(clean_amount)
    if "balance" in df.columns:
        df["balance"] = df["balance"].apply(clean_amount)

    for c in ["txn_date", "narration", "reference", "dr_cr"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    return df


def main():
    # reset log each run
    LOG_FILE.write_text("", encoding="utf-8")

    pdf_files = sorted(PDF_DIR.glob("*.pdf"))[:100]
    if not pdf_files:
        log("No PDFs found in data folder.")
        return

    log(f"Found {len(pdf_files)} PDFs. Starting batch extraction...")

    accounts = []
    txns_list = []
    failed = []

    for i, pdf_path in enumerate(pdf_files, start=1):
        log(f"START {i}/{len(pdf_files)} -> {pdf_path.name}")

        try:
            acc = extract_account_info(pdf_path)
            accounts.append(acc)

            txns = extract_transactions(pdf_path)
            if not txns.empty:
                txns.insert(0, "pdf_file", pdf_path.name)
                txns.insert(1, "account_number", acc.get("account_number"))
                txns_list.append(txns)

            log(f"DONE  {i}/{len(pdf_files)} -> rows={len(txns)}")

        except Exception as e:
            failed.append({"pdf_file": pdf_path.name, "error": str(e)})
            log(f"FAIL  {i}/{len(pdf_files)} -> {pdf_path.name} | {e}")

    accounts_df = pd.DataFrame(accounts)
    txns_df = pd.concat(txns_list, ignore_index=True) if txns_list else pd.DataFrame()

    accounts_df.to_csv(OUT_DIR / "accounts_all.csv", index=False)
    txns_df.to_csv(OUT_DIR / "transactions_all.csv", index=False)

    log("DONE ✅ Saved output/accounts_all.csv and output/transactions_all.csv")
    log(f"Accounts rows: {len(accounts_df)} | Transactions rows: {len(txns_df)}")

    if failed:
        pd.DataFrame(failed).to_csv(OUT_DIR / "failed_files.csv", index=False)
        log(f"Some PDFs failed: {len(failed)} (see output/failed_files.csv)")


if __name__ == "__main__":
    main()
