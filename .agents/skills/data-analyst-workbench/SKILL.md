---
name: data-analyst-workbench
description: End-to-end data analyst workbench CLI implementing a 7-stage audited pipeline (Sources -> Extract -> Staging -> Source Validation/Quarantine -> Transform -> Target Validation/Load -> Business Intelligence) with Checkpoint Engine (What, Why, How), connecting DuckDB, SQLite, Polars, Pandas, Excel, VisiData, Plotext, Rich, Evidence.dev, and Marp.
---

# Data Analyst Workbench Skill

The **Data Analyst Workbench** is a lightweight, code-first, audited analytics toolkit designed for professional data analysts. It integrates open-source analytics engines into a unified CLI workflow (`analyst` / `workbench`):

- **DuckDB:** Embedded high-performance OLAP SQL database engine.
- **SQLite (`sqlite3`):** Row-oriented OLTP database engine for operational transaction ingestion.
- **Polars (Core) & Pandas (Interop Bridge):** Blazing-fast in-memory DataFrame transformations with zero-copy `.to_pandas()` interoperability.
- **Excel Engine (`openpyxl` & `fastexcel`):** Multi-sheet Excel (`.xlsx`, `.xls`) parsing and data hygiene.
- **Checkpoint & Quarantine Audit Engine:** Stage-by-stage transparency recording **What**, **Why**, and **How** at every transition, plus automated exception quarantine (`data/quarantine/error_log.json`).
- **VisiData (`vd`):** Terminal spreadsheet for interactive cell auditing.
- **Plotext & Rich:** Terminal ASCII/Unicode charting, styled tables, and schema profiling.
- **Evidence.dev:** Markdown + SQL interactive web BI dashboards.
- **Marp:** Markdown to executive presentation slides (HTML/PDF).

---

## 7-Stage Audited Pipeline Architecture

Every project follows a strict, resilient 7-stage data engineering & analytics workflow:

```
[ 1. SOURCES ] (SQLite OLTP, Excel/CSV, JSON, Laravel MySQL/Postgres, n8n Inbound)
       │
       ▼
[ 2. EXTRACT ] ────────────────► Checkpoint 1 (What, Why, How)
       │
       ▼
[ 3. STAGING / LANDING ] ──────► Checkpoint 2 (Immutable Raw Parquet in data/staging/)
       │
       ▼
[ 4. SOURCE VALIDATION ] ──────► Checkpoint 3 (Gate 1: Validasi Awal)
  ├── PASSED ──► Continue
  └── FAILED ──► Quarantine / Exception Log (data/quarantine/error_log.json & CSV)
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

## Core CLI Workflows

### 1. Portfolio Management & Health
```powershell
# Health check of all integrated Python & CLI tools
analyst doctor

# Track all projects in portfolio
analyst list

# Manage workbench defaults (project folder, AI API key)
analyst config
analyst config --set-dir "C:\Projects\data_analyst"
analyst config --set-key "<API_KEY>"
```

### 2. Project Scaffolding
```powershell
# Scaffold into default projects folder
analyst new pizza-sales --template restaurant-sales

# Scaffold to a custom path
analyst new mokopi-analytics --path "C:\Projects\data_analyst"
```

Project layout created:
```
<project-name>/
├── data/
│   ├── raw/                 <- Source SQLite (.db), Excel (.xlsx), CSV, JSON
│   ├── staging/             <- Immutable raw Parquet landing snapshots
│   ├── quarantine/          <- Rejected rows CSV & error_log.json (Exception Log)
│   ├── checkpoints/         <- Audit manifests (run_latest.json & history)
│   ├── processed/ & marts/  <- Cleaned analytical Parquet marts
│   └── analytics.duckdb     <- Persistent DuckDB OLAP database
├── models/
│   ├── data_dictionary.md   <- Governance, schema & business metric definitions
│   └── marts.sql            <- Analytical SQL models
├── etl.py                   <- 7-Stage Polars & DuckDB audited ETL pipeline
├── reports/                 <- Evidence.dev interactive BI dashboard
│   ├── evidence.config.yaml
│   └── pages/home.md        <- Dashboard pages (Markdown + SQL)
├── slides/
│   └── presentation.md      <- Marp stakeholder slide deck
└── README.md
```

### 3. Data Hygiene & Profiling
```powershell
# Interactive spreadsheet audit (VisiData) - supports CSV, Excel, SQLite, Parquet
analyst inspect data/raw/pos_transactions.db
analyst inspect data/raw/branch_targets.csv

# Schema profile, null checks & terminal histogram (Polars + Plotext)
analyst stats data/raw/branch_targets.csv
analyst stats data/raw/pos_transactions.db
```

### 4. Audited ETL Execution & Checkpoints (What, Why, How)
```powershell
# Execute the 7-Stage ETL pipeline
analyst run

# Execute interactively (pauses at each checkpoint for user confirmation)
analyst run --interactive

# Inspect latest checkpoint report (What, Why, How table)
analyst checkpoint

# Inspect quarantined / rejected records log
analyst checkpoint --quarantine

# List historical checkpoint runs
analyst checkpoint --list
```

### 5. Analytical SQL Querying
```powershell
# Run ad-hoc SQL query against DuckDB
analyst query "SELECT * FROM mart_store_performance;"

# Execute a SQL model file
analyst query models/marts.sql
```

### 6. Stakeholder Deliverables (Dashboards & Slides)
```powershell
# Launch local Evidence.dev BI dashboard server (http://localhost:3000)
analyst dashboard

# Compile Marp executive slides to HTML or PDF
analyst slides --format html
analyst slides --format pdf
```

### 7. In-Terminal AI Co-Pilot
```powershell
# Ask questions in plain English; AI writes SQL, runs it, and provides takeaways
analyst ask "Which item had the highest gross profit and margin percentage?"
```

---

## Upstream Ecosystem Integration (Laravel, n8n, Pandas)

1. **Laravel / Operational RDBMS (Upstream Source):**
   - Connect directly from `etl.py` or DuckDB using native database connectors (`ATTACH 'host=... dbname=laravel' AS app_db (TYPE MYSQL)` or `pl.read_database()`). Never install PHP/Laravel inside the analytics CLI.
2. **n8n Workflow Automation (Upstream Dispatcher):**
   - Use n8n externally to fetch branch Excel files from Telegram/Email/Google Drive into `data/raw/`, then trigger `analyst run` and `analyst slides --format pdf` via CLI command execution node.
3. **Pandas Interoperability:**
   - Use Polars for fast core ETL, and invoke `.to_pandas()` whenever scikit-learn, statsmodels, or legacy Pandas functions are needed.

---

## Guidelines for Agents Using This Skill

1. **Always verify checkpoints:** After running `analyst run`, inspect `analyst checkpoint` (or `data/checkpoints/run_latest.json`) to report exact row counts, quarantined anomalies, and reconciliation status to the user.
2. **Never silently drop data:** In custom `etl.py` modifications, route invalid rows to `data/quarantine/` using `tracker.log_quarantine(...)` and record **What, Why, How** via `tracker.record_stage(...)`.
3. **Verify before querying:** Run `analyst stats <file>` to inspect column types and nulls before formulating complex SQL joins or models.
