---
name: data-analyst-workbench
description: End-to-end data analyst workbench CLI connecting DuckDB, Polars, VisiData, Plotext, Rich, Evidence.dev (BI dashboards), and Marp (presentation slides). Use when asked to scaffold, audit, profile, transform, query, visualize, or present data analysis projects, or when conducting analytics tasks with the analyst CLI.
---

# Data Analyst Workbench Skill

The **Data Analyst Workbench** is a lightweight, code-first analytics toolkit designed for professional data analysts. It integrates seven open-source tools into a unified CLI workflow (`analyst` / `workbench`):

- **DuckDB:** Embedded OLAP database engine.
- **Polars:** Ultra-fast DataFrame transformations.
- **VisiData (`vd`):** Terminal spreadsheet for interactive cell auditing.
- **Plotext:** Terminal ASCII/Unicode charting.
- **Rich:** Styled tables and schema profiling.
- **Evidence.dev:** Markdown + SQL interactive web BI dashboards.
- **Marp:** Markdown to executive presentation slides (HTML/PDF).

---

## When to Use This Skill

Activate this skill when:
- The user asks to scaffold a new data analysis project for a specific context (sales, restaurant, churn, inventory, retail, marketing).
- The user needs to inspect, clean, or audit datasets in the terminal.
- The user wants to profile schema, data types, null percentages, or distributions.
- The user needs to run fast analytical SQL queries against local Parquet, CSV, or DuckDB files.
- The user wants an interactive web BI dashboard using **Evidence.dev**.
- The user needs to export findings into an executive slide deck using **Marp**.
- The user wants natural language querying via the in-terminal AI co-pilot (`analyst ask`).

---

## Core CLI Workflows

### 1. Portfolio Management & Health
```powershell
# Health check of all 7 integrated tools
analyst doctor

# Track all projects in portfolio
analyst list

# Manage workbench defaults (project folder, AI API key)
analyst config
analyst config --set-dir "C:\Users\my pc\AnalystProjects"
analyst config --set-key "<API_KEY>"
```

### 2. Project Scaffolding
```powershell
# Scaffold into default projects folder
analyst new pizza-sales --template restaurant-sales

# Scaffold to a custom path
analyst new revenue-audit --path "D:\Projects"
```

Project layout created:
```
<project-name>/
├── data/
│   ├── raw/             <- Source CSV / JSON files
│   ├── processed/       <- Cleaned Parquet files
│   └── analytics.duckdb <- Persistent DuckDB database
├── models/
│   └── queries.sql      <- Analytical SQL models
├── etl.py               <- Polars & DuckDB transformation pipeline
├── reports/             <- Evidence.dev interactive BI dashboard
│   ├── evidence.config.yaml
│   └── pages/home.md    <- Dashboard pages (Markdown + SQL)
├── slides/
│   └── presentation.md  <- Marp stakeholder slide deck
└── README.md
```

### 3. Data Hygiene & Profiling
```powershell
# Interactive spreadsheet audit (VisiData)
analyst inspect data/raw/pizza_sales.csv

# Schema profile, null checks & terminal histogram (Polars + Plotext)
analyst stats data/raw/pizza_sales.csv
```

### 4. Data Transformation & SQL Modeling
```powershell
# Execute the Polars & DuckDB ETL script
analyst run

# Run ad-hoc SQL query against DuckDB
analyst query "SELECT category, count(*), sum(total_amount) FROM orders GROUP BY category;"

# Execute a SQL model file
analyst query models/queries.sql
```

### 5. Stakeholder Deliverables (Dashboards & Slides)
```powershell
# Launch local Evidence.dev BI dashboard server (http://localhost:3000)
analyst dashboard

# Compile Marp executive slides to HTML or PDF
analyst slides --format html
analyst slides --format pdf
```

### 6. In-Terminal AI Co-Pilot
```powershell
# Ask questions in plain English; AI writes SQL, runs it, and provides takeaways
analyst ask "Which item had the highest revenue, and what was its ticket share?"
```

---

## Guidelines for Agents Using This Skill

1. **Keep projects organized:** Always use `analyst new` so projects adhere to the standard folder structure.
2. **Verify before querying:** Run `analyst stats <file>` to inspect column types and nulls before formulating complex SQL joins or models.
3. **Use DuckDB views:** In `etl.py`, register processed Parquet files as views or tables in `data/analytics.duckdb` so both Evidence and the CLI can query them immediately.
4. **Syntax in Evidence:** In `reports/pages/home.md`, use built-in Evidence Markdoc components like `{% big_value ... %}`, `{% bar_chart ... %}`, and `{% table ... %}`.
5. **Universal Portability:** Avoid OS-specific shell hacks; all file paths and tools should run cleanly across Windows, macOS, and Linux.
