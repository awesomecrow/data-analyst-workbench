# 🛠️ Data Analyst Workbench

A fast, open-source, and context-aware CLI toolkit tailored for a professional Data Analyst career. It connects local terminal exploration, ultra-fast OLAP SQL, Python data wrangling, interactive BI dashboards, and stakeholder presentations into a cohesive, single-command workflow.

## 🧰 Integrated Open-Source Stack

1. **DuckDB:** Embedded high-performance OLAP SQL database.
2. **Polars:** Blazing fast Python DataFrame library for data transformation.
3. **VisiData (`vd`):** Terminal-based interactive spreadsheet for instant data auditing.
4. **Plotext:** Terminal charting for instant statistical distribution previews.
5. **Rich:** Formatted tables, terminal styling, and schema inspector.
6. **Evidence.dev:** Code-first BI dashboard powered by Markdown + SQL.
7. **Marp:** Markdown presentation slides for executive readouts (HTML/PDF).

---

## 🚀 Quickstart & Installation

Install the workbench CLI locally in editable mode:

```powershell
pip install -e "C:\Users\my pc\.gemini\antigravity\scratch\data-analyst-workbench"
```

Verify your environment:
```powershell
analyst doctor
```

---

## ⚡ Daily Workflow Commands

### 1. Scaffold a Context-Specific Project
Whenever a new stakeholder request or business question arises (e.g. at a pizza restaurant):
```powershell
# In current directory:
analyst new pizza-sales --template restaurant-sales

# In a specific directory using --path / -p:
analyst new pizza-sales --path "C:\Users\my pc\Projects"

# Or provide the full path directly in the name:
analyst new "C:\Users\my pc\Projects\pizza-sales"
```
This generates the full project directory with:
- Raw data files (`data/raw/`)
- Persistent DuckDB database pre-loaded (`data/analytics.duckdb`)
- Polars ETL pipeline script (`etl.py`)
- Analytical SQL models (`models/queries.sql`)
- Interactive Evidence.dev BI dashboard (`reports/`)
- Stakeholder executive Marp slide deck (`slides/presentation.md`)

### 2. Inspect & Audit Data Interactively
Open any dataset in VisiData for rapid cell editing, filtering, and frequency analysis:
```powershell
analyst inspect data/raw/pizza_sales.csv
```

### 3. Profile Schema & Statistical Distribution
Inspect column types, null counts, and view an ASCII histogram in your terminal:
```powershell
analyst stats data/raw/pizza_sales.csv
```

### 4. Run Data Transformations
Execute the Polars/DuckDB data pipeline:
```powershell
analyst run
```

### 5. Query DuckDB Directly
Run queries against your local DuckDB database with beautiful Rich tables:
```powershell
# Inline query
analyst query "SELECT category, count(*), sum(total_amount) FROM orders GROUP BY category;"

# Run from a SQL model file
analyst query models/queries.sql

# Open interactive DuckDB terminal shell
analyst query
```

### 6. Launch the Evidence BI Dashboard
Start your local interactive web dashboard:
```powershell
analyst dashboard
```
Open `http://localhost:3000` to interact with charts, KPI cards, and filters.

### 7. Compile Presentation Slides for Stakeholders
Export your findings to a presentation deck for store managers and executives:
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
analyst ask "Which pizza category generated the most revenue on weekends?"
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
