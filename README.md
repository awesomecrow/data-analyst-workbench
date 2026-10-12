# 🛠️ Data Analyst Workbench

A fast, open-source, and context-aware CLI toolkit tailored for professional Data Analysts. It unifies local terminal exploration, ultra-fast OLAP SQL, Python data wrangling, interactive web BI dashboards, and stakeholder presentations into a cohesive, single-command workflow.

---

## 🧰 Integrated Open-Source Stack

1. **DuckDB:** Embedded high-performance OLAP SQL database engine (analytical marts & fast queries).
2. **SQLite (`sqlite3`):** Row-based OLTP database engine for transactional data simulation and ingestion.
3. **Polars:** Blazing-fast columnar DataFrame library for ETL and data transformation.
4. **Excel Engine (`openpyxl` & `fastexcel`):** Robust Excel (`.xlsx`, `.xls`) parsing and cleaning.
5. **VisiData (`vd`):** Terminal-based interactive spreadsheet for instant cell-level auditing.
6. **Plotext:** Terminal charting for instant statistical distribution previews.
7. **Rich:** Formatted tables, terminal styling, and schema inspector.
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
Whenever a new stakeholder request or business question arises (e.g. at a multi-branch restaurant or retail store):
```powershell
# In default projects directory:
analyst new pizza-sales --template restaurant-sales

# In a specific directory using --path / -p:
analyst new pizza-sales --path "C:\Projects\data_analyst"
```
This generates a standardized project structure:
```
pizza-sales/
├── data/
│   ├── raw/
│   │   ├── pos_transactions.db  <- Normalized SQLite OLTP database (stores, orders, items)
│   │   └── branch_targets.csv   <- Budget/target benchmarks (CSV/Excel)
│   ├── marts/                   <- High-performance Parquet dimensional marts
│   └── analytics.duckdb         <- Persistent DuckDB OLAP database
├── models/
│   ├── data_dictionary.md       <- Schema documentation & metric definitions
│   └── marts.sql                <- Analytical SQL models & business queries
├── etl.py                       <- End-to-end Polars ETL pipeline (OLTP -> OLAP)
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

### 4. Run the ETL Pipeline (OLTP 3NF ➔ OLAP Marts)
Extract transactional row data from SQLite & CSV, clean and transform via Polars, and load into dimensional Parquet marts & DuckDB:
```powershell
analyst run
```

### 5. Query DuckDB Directly
Run queries against your local DuckDB analytical database with formatted Rich tables:
```powershell
# Inline query
analyst query "SELECT * FROM mart_product_performance LIMIT 5;"

# Run from a SQL model file
analyst query models/marts.sql

# Open interactive DuckDB terminal shell
analyst query
```

### 6. Launch the Interactive BI Dashboard
Start your local Evidence.dev web dashboard:
```powershell
analyst dashboard
```
Open `http://localhost:3000` to interact with charts, KPI cards, and filters.

### 7. Compile Presentation Slides for Stakeholders
Export your findings to a slide deck for store managers and executives using Marp:
```powershell
# Compile to HTML slides
analyst slides --format html

# Compile to PDF
analyst slides --format pdf
```

---

## 🤖 AI Co-Pilot & Project Management

### 8. Ask Natural Language Questions (`analyst ask`)
Ask questions in plain English; the AI inspects your DuckDB schema, writes the SQL, executes it, and provides business insights:
```powershell
analyst ask "Which item had the highest revenue and gross profit margin?"
```

### 9. Track Your Entire Project Portfolio (`analyst list`)
List all projects across your designated workspace, including database status, dashboard readiness, and modification dates:
```powershell
analyst list
```

### 10. Configure Default Paths & AI Keys (`analyst config`)
```powershell
# View settings
analyst config

# Set default projects parent directory
analyst config --set-dir "C:\Users\my pc\AnalystProjects"

# Configure AI API key
analyst config --set-key "<YOUR_API_KEY>"

# Set AI provider (gemini, openai, ollama)
analyst config --set-provider gemini
```

---

## 🤝 Contributing & License

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and development workflow.

Licensed under the [MIT License](LICENSE).
