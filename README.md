# 🛠️ Data Analyst Workbench

[![CI Pipeline](https://github.com/awesomecrow/data-analyst-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/awesomecrow/data-analyst-workbench/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-7--Stage%20Audited%20ETL-green.svg)](#-7-stage-audited-pipeline-architecture)

A fast, open-source, and context-aware CLI toolkit tailored for professional Data Analysts. It features a true **Dual-Engine Architecture (SQLite OLTP + DuckDB OLAP)** and implements a resilient **7-Stage Audited ETL Pipeline** with an integrated **Checkpoint & Quarantine Audit Engine (`What`, `Why`, `How`)**—unifying local terminal data exploration, zero-code auto-ingest, OLTP-to-OLAP dimensional modeling, living web BI dashboards, and stakeholder presentations into a single command workflow.

---

## ⚡ The Dual-Engine Advantage

Traditional analytics workflows force a false choice: either run heavy operational databases that crawl on analytical queries, or jump straight to OLAP engines without transactional fidelity. The **Data Analyst Workbench** bridges both:

* **OLTP Engine (Row-Based Relational / SQLite):** Powered by SQLite (`analyst oltp`). Inspect 3NF normalized tables, check primary/foreign keys, test transactional integrity, and run operational queries without running a heavy database daemon.
* **OLAP Engine (Columnar Vectorized / DuckDB):** Powered by DuckDB (`analyst query`). Run sub-second analytical window functions, percentiles, cohort aggregations, and query Parquet files directly.
* **The Bridge (`analyst ingest` & `models/*.sql`):** Auto-discovers any combination of CSVs, Excel sheets, Parquet files, and SQLite databases in `data/raw/`, snapshots them to immutable `data/staging/*.parquet`, and executes declarative SQL models into `data/marts/*.parquet`. Zero boilerplate Python required.

---

## 🏗️ 7-Stage Audited Pipeline Architecture

Every project follows an audited, resilient data engineering workflow with dual validation gates and exception isolation:

```
[ 1. SOURCES ] (SQLite OLTP, Excel, CSV, JSON, Laravel DB, n8n Inbound)
       │
       ▼
[ 2. RAW DATA PLACEMENT ] ────► User places source files into data/raw/
       │
       ▼
[ 3. EXTRACT & STAGING ] ─────► Checkpoints 1 & 2 (Immutable Parquet in data/staging/)
       │
       ▼
[ 4. SOURCE VALIDATION ] ─────► Checkpoint 3 (Gate 1: Pre-Flight Check)
  ├── PASSED (Valid) ────────► Continue to Transform
  └── FAILED (Invalid) ──────► Quarantine / Exception Log (data/quarantine/error_log.json & CSV)
       │
       ▼
[ 5. TRANSFORM ] ─────────────► Checkpoint 4 (Polars Hygiene, Joins, OBT & Star Marts)
       │
       ▼
[ 6. TARGET VALIDATION & LOAD]► Checkpoint 5 & 6 (Gate 2: Reconciliation -> DuckDB & Parquet)
       │
       ▼
[ 7. BUSINESS INTELLIGENCE ] ─► Evidence.dev Web BI, Marp Slides, DuckDB SQL Models
```

---

## 🧰 Integrated Open-Source Analytics Stack

1. **DuckDB:** Embedded high-performance OLAP SQL database engine (analytical marts & sub-second queries).
2. **SQLite (`sqlite3`):** Row-based OLTP database engine for transactional data simulation and ingestion.
3. **Polars (Core) & Pandas (Bridge):** Blazing-fast columnar DataFrame library for ETL, paired with seamless Pandas (`.to_pandas()`) interoperability.
4. **Excel Engine (`openpyxl` & `fastexcel`):** Robust multi-sheet Excel (`.xlsx`, `.xls`) parsing and cleaning.
5. **Checkpoint & Quarantine Engine:** Transparent stage-by-stage audit logging (`What`, `Why`, `How`) and automated exception quarantine (`data/quarantine/`).
6. **VisiData (`vd`):** Terminal-based interactive spreadsheet for instant cell-level auditing.
7. **Plotext & Rich:** Terminal ASCII/Unicode charting, styled tables, and schema profiling.
8. **Evidence.dev:** Code-first BI dashboard powered by Markdown + SQL.
9. **Marp:** Markdown presentation slides for executive readouts (HTML/PDF).

---

## 🚀 Quickstart & Installation

Clone the repository and install in editable mode:

```powershell
git clone https://github.com/awesomecrow/data-analyst-workbench.git
cd data-analyst-workbench
pip install -e .
```

Verify your environment and dependencies:
```powershell
analyst doctor
```

---

## ⚡ Daily Workflow & Commands

### 1. Scaffold a New Analytics Project
Create an isolated workspace for any analytics task:
```powershell
# Create project in default workspace directory
analyst new quarterly_performance

# Or specify a custom destination path:
analyst new quarterly_performance --path "D:\Projects"
```

### 2. Place Your Raw Source Data
Copy your inbound files (Excel spreadsheets, CSV dumps, or SQLite databases) directly into the raw data directory:
```
quarterly_performance/data/raw/
```
> **Best Practice:** Keep raw files immutable. Do not edit them manually so you always maintain an untouched source of truth.

### 3. Explore Operational Data (OLTP Engine)
Inspect normalized 3NF schemas, foreign keys, and run transactional queries:
```powershell
# Inspect 3NF schema, primary keys, and foreign keys
analyst oltp --schema

# Execute a query against operational database
analyst oltp "SELECT customer_id, region FROM customers LIMIT 5;"

# Launch interactive SQLite shell
analyst oltp
```

### 4. Zero-Code Auto-Ingest
Discover all CSV, Excel, Parquet, and SQLite files in `data/raw/` and mount them instantly:
```powershell
analyst ingest
```

### 5. Inspect & Audit Raw Data in Terminal
Open and profile any raw dataset directly in your terminal before running transformations:
```powershell
# Open interactive terminal spreadsheet (VisiData)
analyst inspect data/raw/transactions.xlsx

# Check null counts, schema types, and distribution histograms
analyst stats data/raw/transactions.xlsx
```

### 6. Execute the 7-Stage Audited Pipeline
Run the transformation pipeline (auto-executes custom `etl.py` or declarative `models/*.sql`):
```powershell
# Standard execution
analyst run

# Interactive mode (pauses at each checkpoint for user confirmation)
analyst run --interactive
```

### 7. Inspect Audit Checkpoints & Quarantine Logs
Inspect what happened during data processing without guessing:
```powershell
# View latest stage-by-stage What, Why, How audit report
analyst checkpoint

# View quarantined / rejected records and failure reasons
analyst checkpoint --quarantine

# View history of all past pipeline runs
analyst checkpoint --list
```

### 8. Query Analytical Marts with SQL (OLAP Engine)
Execute fast analytical SQL queries against local DuckDB marts:
```powershell
# Execute analytical model file
analyst query models/marts.sql

# Or execute an inline SQL query:
analyst query "SELECT * FROM mart_store_performance LIMIT 5;"
```

### 9. Generate Stakeholder Deliverables

#### Interactive Web BI Dashboard
```powershell
# Launch 100% offline interactive BI dashboard (ECharts + DataTables on http://localhost:3000)
analyst dashboard

# Or launch Evidence Studio dev server (if configured):
analyst dashboard --evidence
```

#### Executive Presentation Slide Deck (Marp)
```powershell
# Compile to presentation-ready HTML slides
analyst slides --format html

# Compile to executive PDF document
analyst slides --format pdf
```

---

## 🤖 AI Co-Pilot & Project Management

```powershell
# Ask natural language questions (AI writes SQL and analyzes results)
analyst ask "Which item had the highest revenue and gross profit margin?"

# List and monitor all analytics projects in your workspace
analyst list

# Manage configuration (default workspace path & AI API keys)
analyst config --set-dir "D:\Projects"
analyst config --set-key "<API_KEY>"
analyst config --set-provider gemini
```

---

## 🤝 Contributing & License

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on code standards and pull request workflows.

Licensed under the [MIT License](LICENSE).
