from pathlib import Path
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = BASE_DIR / "output"

ACCOUNTS_CSV = OUT_DIR / "accounts_all.csv"
TXNS_CSV = OUT_DIR / "transactions_all.csv"

st.set_page_config(page_title="Axis Statement Analytics", layout="wide")
st.title("Axis Bank Statement Analytics (Sample Batch)")

st.caption(
    "Pipeline: PDF extraction (pdfplumber) → Cleaning & standardization → CSV/DB storage → Analytics dashboard (Streamlit). "
    "Validated on a 100-statement batch; designed to scale to 1000+ statements."
)

# ---- Load Data ----
if not ACCOUNTS_CSV.exists() or not TXNS_CSV.exists():
    st.error("CSV outputs not found. Run extraction first to create output/accounts_all.csv and output/transactions_all.csv")
    st.stop()

@st.cache_data
def load_data():
    accounts = pd.read_csv(ACCOUNTS_CSV, dtype={"account_number": "string", "customer_id": "string"})
    txns = pd.read_csv(TXNS_CSV, dtype={"account_number": "string"})
    return accounts, txns

accounts, txns = load_data()

# ---- Sidebar Filters ----
st.sidebar.header("Filters")

acct_list = accounts["account_number"].dropna().unique().tolist()
acct_list = sorted([a for a in acct_list if a and a.strip() != ""])

selected_acct = st.sidebar.selectbox("Select Account Number", acct_list)

cust_acc = accounts[accounts["account_number"] == selected_acct].head(1)
cust_txn = txns[txns["account_number"] == selected_acct].copy()

# Convert date
cust_txn["txn_date"] = pd.to_datetime(cust_txn["txn_date"], errors="coerce", dayfirst=True)
cust_txn = cust_txn.dropna(subset=["txn_date"])

# ---- Simple categorization (keyword based) ----
def categorize(narr: str) -> str:
    n = str(narr).upper()
    if "UPI" in n:
        return "UPI"
    if "POS" in n or "CARD" in n:
        return "Card/POS"
    if "ATM" in n:
        return "ATM"
    if "NEFT" in n:
        return "NEFT"
    if "IMPS" in n:
        return "IMPS"
    if "ACH" in n or "ECS" in n:
        return "ACH/ECS"
    if "SALARY" in n:
        return "Salary"
    if "RENT" in n:
        return "Rent"
    if any(x in n for x in ["HOTSTAR", "NETFLIX", "PRIME", "SPOTIFY"]):
        return "Subscriptions"
    if any(x in n for x in ["SWIGGY", "ZOMATO", "EATSURE"]):
        return "Food Delivery"
    if any(x in n for x in ["AMAZON", "FLIPKART", "MYNTRA", "MEESHO"]):
        return "Shopping"
    return "Others"

cust_txn["category"] = cust_txn["narration"].apply(categorize)

# Month column
cust_txn["month"] = cust_txn["txn_date"].dt.to_period("M").astype(str)

# Sort
cust_txn_sorted = cust_txn.sort_values("txn_date", ascending=False)

# ---- Layout ----
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Account Summary")
    st.dataframe(cust_acc, use_container_width=True)

with col2:
    st.subheader("Transactions (Latest 50)")
    st.dataframe(cust_txn_sorted.head(50), use_container_width=True)

# ---- KPIs ----
st.subheader("KPIs (Selected Account)")
k1, k2, k3, k4 = st.columns(4)

total_debit = cust_txn["debit"].fillna(0).sum() if "debit" in cust_txn.columns else 0
total_credit = cust_txn["credit"].fillna(0).sum() if "credit" in cust_txn.columns else 0
txn_count = len(cust_txn)
net_flow = total_credit - total_debit

k1.metric("Total Debit", f"{total_debit:,.2f}")
k2.metric("Total Credit", f"{total_credit:,.2f}")
k3.metric("Transactions", f"{txn_count:,}")
k4.metric("Net Cashflow", f"{net_flow:,.2f}")

# ---- Alerts ----
st.subheader("Alerts")

latest_balance = cust_txn_sorted["balance"].dropna().head(1)
latest_balance_val = float(latest_balance.iloc[0]) if len(latest_balance) else None

large_debits = cust_txn[cust_txn["debit"].fillna(0) >= 10000].sort_values("debit", ascending=False).head(10)

if latest_balance_val is not None and latest_balance_val < 5000:
    st.warning(f"Low balance alert: Latest balance is {latest_balance_val:,.2f}")
else:
    st.success("No low-balance alert triggered (based on latest available balance).")

if len(large_debits):
    st.info("Large debit transactions (>= 10,000):")
    st.dataframe(large_debits[["txn_date", "narration", "debit", "balance"]], use_container_width=True)
else:
    st.write("No large debit transactions found for this account (>= 10,000).")

# ---- Charts ----
st.subheader("Spending & Activity Trends")
c1, c2 = st.columns(2)

with c1:
    st.markdown("**Monthly Debit vs Credit**")
    monthly = cust_txn.groupby("month", as_index=False)[["debit", "credit"]].sum()
    monthly = monthly.sort_values("month")
    st.line_chart(monthly.set_index("month")[["debit", "credit"]])

with c2:
    st.markdown("**Category-wise Debit (Top 10)**")
    cat = cust_txn.groupby("category", as_index=False)["debit"].sum()
    cat = cat.sort_values("debit", ascending=False).head(10)
    st.bar_chart(cat.set_index("category")["debit"])

# ---- Top Merchants ----
st.subheader("Top Merchants / Payees (by Debit)")

merchant = cust_txn.copy()
merchant["merchant"] = merchant["narration"].astype(str).str.upper()

# Extract merchant strings after UPI/xxxxxx/ and POS/xxxxxx/
merchant["merchant"] = merchant["merchant"].str.replace(r"^UPI/[^/]+/", "", regex=True)
merchant["merchant"] = merchant["merchant"].str.replace(r"^POS/[^/]+/", "", regex=True)

# Remove card tail like /CARD **1234
merchant["merchant"] = merchant["merchant"].str.replace(r"/CARD.*$", "", regex=True).str.strip()

top_merchants = merchant.groupby("merchant", as_index=False)["debit"].sum()
top_merchants = top_merchants.sort_values("debit", ascending=False).head(10)

st.bar_chart(top_merchants.set_index("merchant")["debit"])

# ---- Management View ----
st.subheader("Management View (All Accounts in Batch)")

m1, m2, m3 = st.columns(3)
m1.metric("Accounts Processed", f"{len(accounts):,}")
m2.metric("Total Transactions", f"{len(txns):,}")

if "closing_balance" in accounts.columns:
    neg = (pd.to_numeric(accounts["closing_balance"], errors="coerce").fillna(0) < 0).sum()
    m3.metric("Negative Closing Balance Accounts", f"{neg:,}")
else:
    m3.metric("Negative Closing Balance Accounts", "N/A")

st.markdown("**Branch-wise Accounts (Top 10)**")
if "branch" in accounts.columns:
    branch_counts = accounts["branch"].fillna("Unknown").value_counts().head(10)
    st.bar_chart(branch_counts)

st.divider()
st.subheader("Downloads")
st.download_button("Download accounts_all.csv", data=ACCOUNTS_CSV.read_bytes(), file_name="accounts_all.csv")
st.download_button("Download transactions_all.csv", data=TXNS_CSV.read_bytes(), file_name="transactions_all.csv")
