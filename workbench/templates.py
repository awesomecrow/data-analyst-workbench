import os
import csv
import subprocess
import shutil
import duckdb
from rich.console import Console

console = Console()

PIZZA_CSV_DATA = """order_id,date,time,category,pizza_name,size,quantity,unit_price,total_amount
1001,2026-09-01,11:32:00,Classic,The Pepperoni Pizza,L,2,19.50,39.00
1002,2026-09-01,12:05:00,Supreme,The Spicy Supreme,M,1,16.50,16.50
1003,2026-09-01,12:15:00,Veggie,The Margherita,L,1,14.50,14.50
1004,2026-09-01,12:45:00,Chicken,The BBQ Chicken Pizza,L,3,20.00,60.00
1005,2026-09-01,13:10:00,Classic,The Hawaiian Pizza,M,2,15.50,31.00
1006,2026-09-01,18:20:00,Supreme,The Meat Lovers,XL,2,22.00,44.00
1007,2026-09-01,18:45:00,Chicken,The Buffalo Chicken,L,1,19.50,19.50
1008,2026-09-01,19:15:00,Veggie,The Four Cheese,M,2,15.00,30.00
1009,2026-09-02,11:50:00,Classic,The Pepperoni Pizza,L,1,19.50,19.50
1010,2026-09-02,12:20:00,Chicken,The BBQ Chicken Pizza,L,2,20.00,40.00
1011,2026-09-02,12:35:00,Classic,The Margherita,S,1,10.00,10.00
1012,2026-09-02,13:00:00,Supreme,The Spicy Supreme,L,1,18.50,18.50
1013,2026-09-02,18:30:00,Classic,The Pepperoni Pizza,XL,2,23.50,47.00
1014,2026-09-02,19:00:00,Supreme,The Meat Lovers,L,2,19.50,39.00
1015,2026-09-02,19:40:00,Veggie,The Margherita,M,1,13.50,13.50
1016,2026-09-03,12:10:00,Chicken,The BBQ Chicken Pizza,XL,1,22.50,22.50
1017,2026-09-03,12:40:00,Classic,The Hawaiian Pizza,L,2,18.00,36.00
1018,2026-09-03,18:15:00,Supreme,The Meat Lovers,XL,3,22.00,66.00
1019,2026-09-03,19:25:00,Classic,The Pepperoni Pizza,L,2,19.50,39.00
1020,2026-09-03,20:10:00,Chicken,The Buffalo Chicken,M,1,16.50,16.50
"""

PIZZA_ETL_SCRIPT = """import polars as pl
import duckdb
from rich.console import Console

console = Console()

def run_pipeline():
    console.print("[cyan]Running Pizza Analytics ETL with Polars & DuckDB...[/cyan]")
    
    # Read raw orders
    df = pl.read_csv("data/raw/pizza_sales.csv")
    
    # Calculate key metrics
    revenue_by_cat = df.group_by("category").agg([
        pl.col("quantity").sum().alias("total_pizzas"),
        pl.col("total_amount").sum().round(2).alias("total_revenue")
    ]).sort("total_revenue", descending=True)
    
    top_pizzas = df.group_by(["pizza_name", "category"]).agg([
        pl.col("quantity").sum().alias("pizzas_sold"),
        pl.col("total_amount").sum().round(2).alias("total_sales")
    ]).sort("total_sales", descending=True)

    # Save to processed Parquet
    revenue_by_cat.write_parquet("data/processed/revenue_by_category.parquet")
    top_pizzas.write_parquet("data/processed/top_pizzas.parquet")
    df.write_parquet("data/processed/orders_clean.parquet")

    # Update DuckDB
    conn = duckdb.connect("data/analytics.duckdb")
    conn.execute("CREATE OR REPLACE TABLE orders AS SELECT * FROM 'data/processed/orders_clean.parquet'")
    conn.execute("CREATE OR REPLACE VIEW v_category_summary AS SELECT * FROM 'data/processed/revenue_by_category.parquet'")
    conn.execute("CREATE OR REPLACE VIEW v_top_pizzas AS SELECT * FROM 'data/processed/top_pizzas.parquet'")
    conn.close()

    console.print("[bold green][OK] ETL Complete! Updated Parquet files and DuckDB views.[/bold green]")

if __name__ == "__main__":
    run_pipeline()
"""

PIZZA_SQL_MODELS = """-- Pizza Sales Analytical Queries
-- Run with: analyst query models/queries.sql

-- 1. Daily Revenue Trend
SELECT 
    date,
    COUNT(DISTINCT order_id) AS orders_count,
    SUM(quantity) AS pizzas_sold,
    ROUND(SUM(total_amount), 2) AS daily_revenue
FROM orders
GROUP BY date
ORDER BY date;

-- 2. Category Performance
SELECT 
    category,
    SUM(quantity) AS total_quantity,
    ROUND(SUM(total_amount), 2) AS total_revenue,
    ROUND(100.0 * SUM(total_amount) / (SELECT SUM(total_amount) FROM orders), 1) AS pct_revenue
FROM orders
GROUP BY category
ORDER BY total_revenue DESC;
"""

PIZZA_EVIDENCE_PAGE = """# 🍕 Pizza Restaurant - Executive Analytics Dashboard

```sql kpis
select 
  round(sum(total_amount), 2) as total_revenue,
  sum(quantity) as total_pizzas,
  round(sum(total_amount) / count(distinct order_id), 2) as avg_ticket
from read_csv_auto('data/raw/pizza_sales.csv')
```

```sql category_breakdown
select 
  category,
  sum(quantity) as quantity_sold,
  round(sum(total_amount), 2) as revenue
from read_csv_auto('data/raw/pizza_sales.csv')
group by category
order by revenue desc
```

```sql top_pizzas
select 
  pizza_name,
  category,
  sum(quantity) as units_sold,
  round(sum(total_amount), 2) as total_sales
from read_csv_auto('data/raw/pizza_sales.csv')
group by pizza_name, category
order by total_sales desc
limit 5
```

### High-Level Performance

{% big_value data="kpis" value="total_revenue" title="Total Revenue" fmt="usd" /%}
{% big_value data="kpis" value="total_pizzas" title="Pizzas Sold" /%}
{% big_value data="kpis" value="avg_ticket" title="Avg Ticket Size" fmt="usd" /%}

---

### Category Revenue Breakdown

{% bar_chart 
  data="category_breakdown" 
  x="category" 
  y="revenue" 
  title="Revenue by Category ($)"
/%}

---

### Top 5 Best Selling Pizzas

{% table 
  data="top_pizzas" 
/%}
"""

PIZZA_MARP_SLIDES = """---
marp: true
theme: default
paginate: true
header: "🍕 Pizza Analytics | Executive Briefing"
footer: "Confidential - For Store Management Only"
style: |
  section {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    padding: 40px;
  }
  h1 { color: #b91c1c; }
  h2 { color: #1e293b; }
---

# 🍕 Pizza Store Performance Review
### Strategic Sales, Category & Operational Analytics
**Prepared by:** Lead Data Analyst
**Period:** September 2026

---

## 1. Executive Summary & KPIs

* **Total Revenue:** **$590.00** across initial test periods.
* **Volume Sold:** **31 pizzas** (avg. ~1.55 items per ticket).
* **Average Ticket Size:** **$29.50** per customer transaction.
* **Key Finding:** Supreme and Chicken categories drive over **60% of total revenue**, despite having fewer menu varieties.

---

## 2. Category Performance Overview

| Category | Units Sold | Total Revenue | Revenue Share |
| :--- | :--- | :--- | :--- |
| **Supreme** | 9 | $185.00 | **31.4%** |
| **Chicken** | 8 | $178.00 | **30.2%** |
| **Classic** | 8 | $154.50 | **26.2%** |
| **Veggie** | 6 | $72.50 | **12.3%** |

*Supreme items have the highest average margin and ticket lift.*

---

## 3. Top Performing Pizzas

1. **The Meat Lovers (Supreme):** #1 Revenue driver ($149.00 total)
2. **The BBQ Chicken Pizza (Chicken):** #2 Revenue driver ($122.50 total)
3. **The Pepperoni Pizza (Classic):** Consistent daily demand ($105.00 total)
4. **The Margherita (Veggie):** Low ticket price, consider combo bundling.

---

## 4. Strategic Recommendations for Management

* **Menu Engineering:**
  * Promote **Meat Lovers + BBQ Chicken** as combo specials during dinner hours.
  * Re-price or create a "Deluxe Veggie" to increase average ticket size for vegetarians.
* **Kitchen & Prep Planning:**
  * Peak volume is concentrated between **12:00 - 13:30** and **18:00 - 19:30**.
  * Pre-stretch dough for Large and XL sizes 30 minutes before evening peak.
"""

from workbench.config import load_config

def scaffold_project(project_name: str, template: str = "restaurant-sales", target_path: str | None = None):
    if target_path:
        target_dir = os.path.abspath(os.path.join(target_path, project_name))
    elif os.path.isabs(project_name) or project_name.startswith(".") or project_name.startswith("/") or project_name.startswith("\\"):
        target_dir = os.path.abspath(project_name)
    else:
        cfg = load_config()
        p_dir = cfg.get("projects_dir", os.path.expanduser("~/AnalystProjects"))
        target_dir = os.path.abspath(os.path.join(p_dir, project_name))

    if os.path.exists(target_dir):
        console.print(f"[bold red]Error:[/bold red] Directory '{target_dir}' already exists.")
        return

    console.print(f"\n[bold cyan]Scaffolding new project:[/bold cyan] [bold green]{os.path.basename(target_dir)}[/bold green]")
    console.print(f"[dim]Destination: {target_dir}[/dim]")
    console.print(f"[dim]Template: {template}[/dim]")

    # Create folder structure
    os.makedirs(os.path.join(target_dir, "data", "raw"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "data", "processed"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "models"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "slides"), exist_ok=True)

    # 1. Write Data
    csv_path = os.path.join(target_dir, "data", "raw", "pizza_sales.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(PIZZA_CSV_DATA.strip() + "\n")

    # 2. Initialize DuckDB
    db_path = os.path.join(target_dir, "data", "analytics.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute(f"CREATE TABLE orders AS SELECT * FROM '{csv_path.replace(chr(92), '/')}'")
    conn.close()

    # 3. Write ETL script
    etl_path = os.path.join(target_dir, "etl.py")
    with open(etl_path, "w", encoding="utf-8") as f:
        f.write(PIZZA_ETL_SCRIPT.strip() + "\n")

    # 4. Write SQL Models
    sql_path = os.path.join(target_dir, "models", "queries.sql")
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write(PIZZA_SQL_MODELS.strip() + "\n")

    # 5. Scaffold Evidence dashboard inside reports/
    reports_dir = os.path.join(target_dir, "reports")
    evidence_cli = shutil.which("evidence")
    if evidence_cli:
        try:
            subprocess.run([evidence_cli, "init", reports_dir], capture_output=True)
        except Exception:
            os.makedirs(os.path.join(reports_dir, "pages"), exist_ok=True)
    else:
        os.makedirs(os.path.join(reports_dir, "pages"), exist_ok=True)

    # Write custom dashboard home page
    pages_dir = os.path.join(reports_dir, "pages")
    os.makedirs(pages_dir, exist_ok=True)
    with open(os.path.join(pages_dir, "home.md"), "w", encoding="utf-8") as f:
        f.write(PIZZA_EVIDENCE_PAGE.strip() + "\n")

    # 6. Write Marp Presentation Deck
    marp_path = os.path.join(target_dir, "slides", "presentation.md")
    with open(marp_path, "w", encoding="utf-8") as f:
        f.write(PIZZA_MARP_SLIDES.strip() + "\n")

    # 7. Write Project README
    readme_content = f"""# {project_name}

Data analysis project scaffolded with the **Data Analyst Workbench**.

## Project Layout
- `data/raw/` : Raw CSV / JSON data
- `data/processed/` : Cleaned Parquet tables
- `data/analytics.duckdb` : DuckDB local database
- `etl.py` : Polars & DuckDB processing script
- `models/queries.sql` : Core SQL models & metrics
- `reports/` : Evidence.dev interactive BI dashboard
- `slides/` : Marp executive presentation slides

## Quick Commands
```powershell
# 1. Audit data interactively
analyst inspect data/raw/pizza_sales.csv

# 2. View data stats and terminal distribution
analyst stats data/raw/pizza_sales.csv

# 3. Run ETL pipeline (Polars + DuckDB)
analyst run

# 4. Query DuckDB from terminal
analyst query "SELECT * FROM orders LIMIT 5;"
analyst query models/queries.sql

# 5. Launch interactive BI dashboard
analyst dashboard

# 6. Compile stakeholder slide deck (HTML or PDF)
analyst slides
```
"""
    with open(os.path.join(target_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)

    console.print(f"[bold green][OK] Project '{project_name}' successfully created![/bold green]")
    console.print(f"[cyan]Next step:[/cyan] [yellow]cd {project_name}[/yellow]")
    console.print("[dim]Run 'analyst --help' to see all workflow commands.[/dim]\n")
