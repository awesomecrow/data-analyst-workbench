# 🛠️ Data Analyst Workbench

A fast, open-source, and context-aware CLI toolkit tailored for professional Data Analysts. It implements a resilient **7-Stage Audited ETL Pipeline** with a built-in **Checkpoint & Quarantine Engine (What, Why, How)**—unifying terminal data exploration, OLTP-to-OLAP modeling, interactive web BI dashboards, and executive presentations into a single command workflow.

---

## 🏗️ 7-Stage Audited Pipeline Architecture

```
[ 1. SOURCES ] (SQLite OLTP, Excel/CSV, JSON, Laravel DB, n8n Inbound)
       │
       ▼
[ 2. EXTRACT ] ────────────────► Checkpoint 1 (What, Why, How)
       │
       ▼
[ 3. STAGING / LANDING ] ──────► Checkpoint 2 (Immutable Raw Parquet in data/staging/)
       │
       ▼
[ 4. SOURCE VALIDATION ] ──────► Checkpoint 3 (Gate 1: Validasi Awal)
  ├── LULUS (Valid) ──► Continue to Transform
  └── GAGAL (Invalid) ► Quarantine / Error Log (data/quarantine/error_log.json & CSV)
       │
       ▼
[ 5. TRANSFORM ] ──────────────► Checkpoint 4 (Polars Hygiene, Joins, OBT & Star Marts)
       │
       ▼
[ 6. TARGET VALIDATION & LOAD ]► Checkpoint 5 & 6 (Gate 2: Reconciliation -> DuckDB & Parquet)
       │
       ▼
[ 7. BUSINESS INTELLIGENCE ] ──► Evidence.dev Web BI, Marp Slides, DuckDB SQL Models
```

---

## 🧰 Integrated Open-Source Stack

1. **DuckDB:** Embedded high-performance OLAP SQL database engine (analytical marts & fast queries).
2. **SQLite (`sqlite3`):** Row-based OLTP database engine for transactional data simulation and ingestion.
3. **Polars (Core) & Pandas (Interop Bridge):** Blazing-fast columnar DataFrame library for ETL, paired with Pandas (`>=2.0`) interoperability via `.to_pandas()`.
4. **Excel Engine (`openpyxl` & `fastexcel`):** Robust Excel (`.xlsx`, `.xls`) parsing and cleaning.
5. **Checkpoint & Quarantine Engine:** Transparent stage-by-stage audit logging (`What`, `Why`, `How`) and automated exception quarantine (`data/quarantine/`).
6. **VisiData (`vd`):** Terminal-based interactive spreadsheet for instant cell-level auditing.
7. **Plotext & Rich:** Terminal charting, formatted tables, and schema inspector.
8. **Evidence.dev:** Code-first BI dashboard powered by Markdown + SQL.
9. **Marp:** Markdown presentation slides for executive readouts (HTML/PDF).

---

## 🚀 Quickstart & Installation

Clone or navigate to the repository directory, then install in editable mode:

```powershell
cd "C:\Projects\data_analyst\data analyst workbench"
pip install -e .
```

Verify your environment and dependencies:
```powershell
analyst doctor
```

---

## ⚡ Daily Workflow & Commands

### 1. Scaffold a Context-Specific Project
Whenever a new stakeholder request or business question arises:
```powershell
# In default projects directory:
analyst new pizza-sales --template restaurant-sales

# In a specific directory using --path / -p:
analyst new pizza-sales --path "C:\Projects\data_analyst"
```
This generates a standardized 7-stage project structure:
```
pizza-sales/
├── data/
│   ├── raw/
│   │   ├── pos_transactions.db  <- Normalized SQLite OLTP database (stores, orders, items)
│   │   └── branch_targets.csv   <- Budget/target benchmarks (CSV/Excel)
│   ├── staging/                 <- Immutable landing Parquet snapshots
│   ├── quarantine/              <- Rejected rows CSV & error_log.json (Daftar Pengecualian)
│   ├── checkpoints/             <- Audit trail manifests (run_latest.json & history)
│   ├── processed/ & marts/      <- High-performance Parquet dimensional marts
│   └── analytics.duckdb         <- Persistent DuckDB OLAP database
├── models/
│   ├── data_dictionary.md       <- Schema documentation & metric definitions
│   └── marts.sql                <- Analytical SQL models & business queries
├── etl.py                       <- 7-Stage Polars ETL pipeline with CheckpointTracker
├── reports/                     <- Evidence.dev interactive BI dashboard
│   ├── evidence.config.yaml
│   └── pages/home.md            <- Dashboard pages (Markdown + SQL)
├── slides/
│   └── presentation.md          <- Marp executive presentation slide deck
└── README.md
```

### 2. Inspect & Audit Data Interactively
Open any dataset (CSV, JSON, Excel `.xlsx`, or SQLite `.db`) in VisiData for rapid cell editing, filtering, and frequency analysis:
```powershell
analyst inspect data/raw/branch_targets.csv
analyst inspect data/raw/pos_transactions.db
```

### 3. Profile Schema & Statistical Distribution
Inspect column types, null counts, and view an ASCII histogram in your terminal:
```powershell
analyst stats data/raw/branch_targets.csv
analyst stats data/raw/pos_transactions.db
```

### 4. Run the 7-Stage Audited ETL Pipeline
Extract transactional row data, stage raw snapshots, quarantine invalid records, transform via Polars, verify target reconciliation, and load into DuckDB & Parquet:
```powershell
# Standard execution with Checkpoint output
analyst run

# Interactive mode (pauses at each checkpoint for user confirmation)
analyst run --interactive
```

### 5. Inspect Checkpoints (What, Why, How) & Quarantine Logs
Review the complete audit trail of your pipeline run at any time:
```powershell
# Show latest stage-by-stage What, Why, How audit table
analyst checkpoint

# Inspect quarantined records and rejection reasons
analyst checkpoint --quarantine

# List all historical pipeline runs
analyst checkpoint --list
```

### 6. Query DuckDB Directly
Run queries against your local DuckDB analytical database with formatted Rich tables:
```powershell
# Inline query
analyst query "SELECT * FROM mart_store_performance;"

# Run from a SQL model file
analyst query models/marts.sql

# Open interactive DuckDB terminal shell
analyst query
```

### 7. Launch the Interactive BI Dashboard
Start your local Evidence.dev web dashboard:
```powershell
analyst dashboard
```
Open `http://localhost:3000` to interact with charts, KPI cards, and filters.

### 8. Compile Presentation Slides for Stakeholders
Export your findings to a slide deck for store managers and executives using Marp:
```powershell
# Compile to HTML slides
analyst slides --format html

# Compile to PDF
analyst slides --format pdf
```

---

## 🤖 AI Co-Pilot & Project Management

### 9. Ask Natural Language Questions (`analyst ask`)
Ask questions in plain English; the AI inspects your DuckDB schema, writes the SQL, executes it, and provides business insights:
```powershell
analyst ask "Which item had the highest revenue and gross profit margin?"
```

### 10. Track Your Entire Project Portfolio (`analyst list`)
List all projects across your designated workspace, including database status, dashboard readiness, and modification dates:
```powershell
analyst list
```

### 11. Configure Default Paths & AI Keys (`analyst config`)
```powershell
# View settings
analyst config

# Set default projects parent directory
analyst config --set-dir "C:\Projects\data_analyst"

# Configure AI API key
analyst config --set-key "<YOUR_API_KEY>"

# Set AI provider (gemini, openai, ollama)
analyst config --set-provider gemini
```

---

## 🤝 Contributing & License

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and development workflow.

Licensed under the [MIT License](LICENSE).
