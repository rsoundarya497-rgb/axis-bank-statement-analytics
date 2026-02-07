📊 Axis Bank Statement Analytics

PDF Transaction Extraction & Analytics Dashboard

📌 Project Overview

This project automates the extraction and analysis of bank statement PDFs.
It converts unstructured PDF statements into structured, analyzable datasets and presents insights through an interactive Streamlit dashboard.

The project demonstrates a complete end-to-end data engineering pipeline:

PDF ingestion

Data extraction and cleaning

Structured data storage

Interactive analytics and visualization

The pipeline was validated on a sample batch of 100 customer statements and is designed to scale to 1000+ PDFs.

🏗️ Architecture
Development / Local Pipeline
PDF Bank Statements
        ↓
PDF Extraction (pdfplumber)
        ↓
Data Cleaning & Standardization (Python, Pandas)
        ↓
Structured Storage (CSV / DB-ready tables)
        ↓
Analytics Dashboard (Streamlit)

Production / Cloud-Ready Design (Conceptual)
S3 (PDF Upload)
   ↓
AWS Lambda (PDF Parsing & Cleaning)
   ↓
RDS / PostgreSQL (Accounts & Transactions)
   ↓
BI Tool / Streamlit Dashboard

📂 Project Structure
axis_statement_project/
│
├── data/
│   └── *.pdf                 # Bank statement PDFs
│
├── output/
│   ├── accounts_all.csv      # Extracted account-level data
│   ├── transactions_all.csv # Extracted transaction-level data
│   └── run_log.txt           # Processing log
│
├── src/
│   ├── extract_batch.py      # Batch PDF extraction pipeline
│   └── app.py                # Streamlit analytics dashboard
│
└── README.md

🧾 Data Model
1️⃣ Accounts Table (accounts_all.csv)
Column Name	Description
pdf_file	Source PDF file name
account_number	Bank account number
holder_name	Account holder name (nullable)
customer_id / CIF	Customer identifier (nullable)
ifsc_code	IFSC code
branch	Branch name
period_from	Statement start date
period_to	Statement end date
2️⃣ Transactions Table (transactions_all.csv)
Column Name	Description
pdf_file	Source PDF
account_number	Account number
txn_date	Transaction date
narration	Transaction description
reference	Reference number
dr_cr	Debit / Credit indicator
debit	Debit amount
credit	Credit amount
balance	Closing balance
⚙️ Technologies Used

Python

pdfplumber – PDF text and table extraction

Pandas – data cleaning and transformation

Streamlit – interactive analytics dashboard

Regex – intelligent pattern matching

🚀 How to Run the Project
1️⃣ Install Dependencies
pip install pdfplumber pandas streamlit

2️⃣ Place PDFs

Copy all bank statement PDF files into:

data/

3️⃣ Run Batch Extraction
python src/extract_batch.py


This generates:

output/accounts_all.csv

output/transactions_all.csv

4️⃣ Launch Dashboard
streamlit run src/app.py


The dashboard will open automatically in your browser.

📊 Dashboard Features
👤 Customer View

Account summary

Latest transactions

KPIs:

Total debit

Total credit

Net cashflow

Monthly debit vs credit trend

Category-wise spending analysis

Top merchants / payees

Alerts:

Low balance

Large debit transactions

🏦 Management View

Number of accounts processed

Total transactions in batch

Branch-wise account distribution

Risk indicator (negative balance accounts)

⚠️ Real-World Data Handling

Some PDF headers (customer name, CIF) are stored as images or complex layouts.

The pipeline safely handles missing metadata without breaking.

Account number is used as the primary unique identifier.

This reflects real-world banking and data engineering constraints.

📈 Scalability & Performance

Validated on 100 statements (~137k transactions) during development.

Designed to scale linearly to 1000+ PDFs.

Production optimization options:

Parallel processing

Cloud storage (AWS S3)

Serverless compute (AWS Lambda)

Database-backed analytics (PostgreSQL / RDS)

🎯 Key Learning Outcomes

Handling unstructured PDF data

Robust batch-processing pipelines

Data cleaning and validation

Transaction analytics

Building interactive dashboards

Designing scalable data solutions

📌 Disclaimer

This project uses synthetic / anonymized bank statement data for educational and demonstration purposes only.