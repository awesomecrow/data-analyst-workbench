---
name: data-analyst-workbench
description: End-to-end data analyst workbench CLI implementing a Dual-Engine architecture (SQLite OLTP + DuckDB OLAP) and an audited 7-stage pipeline (Sources -> Extract -> Staging -> Source Validation/Quarantine -> Transform -> Target Validation/Load -> Business Intelligence) with Checkpoint Engine (What, Why, How), connecting DuckDB, SQLite, Polars, Pandas, Excel, VisiData, Plotext, Rich, Evidence.dev, and Marp.
---

# Data Analyst Workbench Skill (Dual-Engine OLTP & OLAP)

The **Data Analyst Workbench** is a lightweight, code-first, audited analytics workbench designed for professional data analysts. It bridges transactional operational databases with vectorized analytical data warehouses:

- **OLTP Engine (Row-Based / 3NF Relational):** Powered by **SQLite (`sqlite3`)** via `analyst oltp`. Provides normalized schema inspection, foreign key tracking, transactional queries, and raw state exploration.
- **OLAP Engine (Columnar / Vectorized):** Powered by **DuckDB** via `analyst query`. Provides sub-second analytical aggregations, dimensional marts, and Parquet scanning.
- **The Zero-Code Ingestion Bridge (`analyst ingest`):** Auto-discovers heterogeneous raw files (CSV, Excel, Parquet, SQLite) in `data/raw/`, snapshots them to immutable `data/staging/*.parquet`, and mounts them instantly into DuckDB.
- **Declarative SQL-First Modeling (`models/*.sql`):** Eliminates procedural Python glue code. Analysts write clean SQL transformations that `analyst run` automatically executes into `data/marts/*.parquet`.
- **Data Hygiene & Quarantine Gate:** Isolates anomalies to `data/quarantine/` (`error_log.json` and CSVs) with explicit reasoning.
- **Checkpoint Audit Trail Engine:** Automatically captures **What, Why, and How** across every stage (`analyst checkpoint`).
- **Interactive Offline BI Dashboard (`analyst dashboard`):** Instant, 100% offline executive dashboard with ECharts and searchable DataTables bound directly to DuckDB marts (with optional Evidence Studio support via `--evidence`).
- **Executive Slides (`analyst slides`):** Compiles Marp markdown decks directly into standalone HTML and PDF readouts.
- **Terminal TUI & Profiling:** Interactive spreadsheet auditing via **VisiData (`vd`)** and terminal charting via **Plotext** and **Rich**.

---

## 7-Stage Dual-Engine Pipeline Architecture

```
[ 1. SOURCES (OLTP & Files) ] (SQLite operational.db, CSV, Excel, MySQL snapshot)
       │
       ▼ (Zero-Code Auto-Ingest: analyst ingest)
[ 2. EXTRACT & STAGING ] ────► Checkpoint 1: Immutable Snappy Parquet in data/staging/
       │
       ▼
[ 3. SOURCE VALIDATION ] ────► Checkpoint 2: Gate 1 Pre-Flight Rules (BR-04, BR-10)
  ├── PASSED ──► Continue
  └── FAILED ──► Quarantine Log (data/quarantine/error_log.json & CSV)
       │
       ▼ (Declarative SQL-First: models/*.sql or custom etl.py)
[ 4. SEMANTIC TRANSFORM ] ───► Checkpoint 3: Dimensional Marts & OBT Tables
       │
       ▼
[ 5. TARGET VALIDATION ] ────► Checkpoint 4: Gate 2 Reconciliation & Assertions
       │
       ▼
[ 6. OLAP MART SERVING ] ────► Checkpoint 5: DuckDB Views & data/marts/*.parquet
       │
       ▼
[ 7. DELIVERABLES ] ─────────► analyst dashboard (Offline BI) & analyst slides (Marp)
```

---

## Core CLI Workflows

### 1. Portfolio Health & Environment
```powershell
# Health check of both OLTP (SQLite) and OLAP (DuckDB) engines and tools
analyst doctor

# Track all projects in portfolio
analyst list

# Manage workbench defaults (project folder, AI API key)
analyst config
analyst config --set-dir "C:\Projects\data_analyst"
```

### 2. Project Scaffolding
```powershell
# Scaffold clean, generic Dual-Engine project (default)
analyst new my_analytics_project

# Scaffold to a custom directory path
analyst new swift_route_analytics --path "C:\Projects\data_analyst"

# Scaffold demo restaurant template with sample transactions
analyst new pizza_sales --template restaurant-sales
```

### 3. OLTP Operational Engine (Row-Based / SQLite)
```powershell
# Inspect normalized 3NF relational schema, primary keys, and foreign keys
analyst oltp --schema

# Execute a transactional or operational query against SQLite
analyst oltp "SELECT customer_name, region FROM customers LIMIT 10;"

# Launch interactive SQLite shell
analyst oltp
```

### 4. Zero-Code Auto-Ingestion
```powershell
# Ingest all CSV, Excel, Parquet, and SQLite tables in data/raw/
# Snapshots to data/staging/*.parquet and mounts tables into DuckDB
analyst ingest
```

### 5. Audited Pipeline Execution & Checkpoints (What, Why, How)
```powershell
# Run the pipeline (executes custom etl.py if present, or declarative SQL models in models/*.sql)
analyst run

# Run interactively (pauses at each checkpoint for analyst confirmation)
analyst run --interactive

# View latest checkpoint audit trail (What, Why, How table)
analyst checkpoint

# Inspect quarantined records log (failed business assertions)
analyst checkpoint --quarantine

# View checkpoint run history
analyst checkpoint --list
```

### 6. OLAP Vector Querying (DuckDB)
```powershell
# Query materialized analytical marts inside DuckDB
analyst query "SELECT * FROM mart_hub_performance ORDER BY on_time_rate_pct DESC;"

# Run analytical SQL model file
analyst query models/marts.sql

# Launch interactive DuckDB shell
analyst query
```

### 7. Data Exploration & Terminal Profiling
```powershell
# Interactive spreadsheet audit in terminal (VisiData)
analyst inspect data/raw/operational.db
analyst inspect data/staging/shipments.parquet

# Statistical schema profiling, null counts & terminal charts (Polars + Plotext)
analyst stats data/raw/shipments.csv
```

### 8. Living Deliverables (Dashboards & Slides)
```powershell
# Launch 100% offline interactive BI dashboard (ECharts + DataTables on http://localhost:3000)
analyst dashboard

# Launch on a custom port
analyst dashboard --port 8080

# Launch Evidence Studio dev server (requires Evidence Studio login / warehouse)
analyst dashboard --evidence

# Compile executive presentation slides via Marp
analyst slides --format html
analyst slides --format pdf
```

### 9. Natural Language AI Co-Pilot
```powershell
# Ask questions in plain English; AI writes SQL, runs it, and provides takeaways
analyst ask "Which hub had the lowest on-time delivery rate and why?"
```

---

## Guidelines for Agents Using This Skill

1. **Dual-Engine Division of Labor:**
   - Use `analyst oltp` for operational entities, transaction logs, and 3NF normalization.
   - Use `analyst query` for analytical questions, cohort metrics, percentiles, and SLA scorecards.
2. **Zero-Code First:** Drop raw files into `data/raw/` and run `analyst ingest` before writing any procedural python code.
3. **Always verify checkpoints:** Run `analyst checkpoint` after pipeline execution to confirm row conservation and quarantine logs.
4. **Never silently drop rows:** Offending rows must route to `data/quarantine/` with an audit reason logged in `error_log.json`.
5. **Living deliverables over static text:** Always recompile slides (`analyst slides`) and regenerate dashboards (`analyst dashboard`) when data changes.
