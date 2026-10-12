import os
import csv
import subprocess
import shutil
import sqlite3
import duckdb
from rich.console import Console

from workbench.config import load_config

console = Console()

BRANCH_TARGETS_CSV = """store_id,store_name,monthly_target,target_volume
1,Downtown Flagship,600.00,35
2,Uptown Mall,450.00,25
3,Suburban Express,300.00,20
"""

DATA_DICTIONARY_MD = """# Data Dictionary & Business Metric Definitions

## Business Metric Definitions
* **Gross Sales ($):** Total sales value before discounts (`quantity * unit_price`).
* **Discount ($):** Value of promotion, voucher, or loyalty rebate applied.
* **Net Revenue ($):** Realized income received from the customer (`gross_sales - discount_amount`).
* **Cost of Goods Sold / COGS ($):** Direct ingredient and packaging cost (`quantity * cogs`).
* **Gross Profit ($):** Dollar contribution after ingredient costs (`net_revenue - total_cogs`).
* **Gross Margin (%):** Profitability efficiency (`(gross_profit / net_revenue) * 100`).
* **Average Ticket Size / AOV ($):** Average customer spend per transaction (`net_revenue / distinct_orders`).
* **Target Attainment (%):** Store achievement vs monthly revenue budget (`(actual_revenue / monthly_target) * 100`).

---

## OLTP Source Schema (`data/raw/pos_transactions.db` - SQLite)
* `stores`: `(store_id INT, store_name TEXT, city TEXT, store_type TEXT)`
* `categories`: `(category_id INT, category_name TEXT)`
* `menu_items`: `(menu_id INT, menu_name TEXT, category_id INT, unit_price REAL, cogs REAL)`
* `orders`: `(order_id INT, order_datetime TEXT, store_id INT, customer_id INT, payment_method TEXT, order_status TEXT)`
* `order_items`: `(item_id INT, order_id INT, menu_id INT, quantity INT, discount_amount REAL)`

---

## OLAP Analytical Target Schema (`data/analytics.duckdb` & Parquet)
* `fact_order_details`: Denormalized One Big Table (OBT) detailing line-item performance, margins, and store metadata.
* `mart_store_performance`: Store-level aggregates joined with executive targets.
* `mart_menu_profitability`: Product-level margin contribution and sales volume ranking.
"""

SQL_MODELS_CONTENT = """-- Analytical SQL Models (OLAP)
-- Run with: analyst query models/marts.sql

-- 1. Store Target Attainment & Profitability
SELECT 
    store_name,
    actual_orders,
    actual_volume,
    actual_revenue,
    monthly_target,
    ROUND(attainment_pct, 1) AS attainment_pct,
    actual_profit,
    ROUND(margin_pct, 1) AS profit_margin_pct
FROM mart_store_performance
ORDER BY actual_revenue DESC;

-- 2. Menu Item Profit Contribution Matrix
SELECT 
    menu_name,
    category_name,
    units_sold,
    net_revenue,
    gross_profit,
    ROUND(profit_margin_pct, 1) AS margin_pct
FROM mart_menu_profitability
ORDER BY gross_profit DESC;
"""

ETL_PIPELINE_SCRIPT = """import os
import sqlite3
import polars as pl
import duckdb
from rich.console import Console

console = Console()

def run_etl():
    console.print("[bold cyan]Starting End-to-End ETL Pipeline (OLTP -> OLAP)...[/bold cyan]")
    
    # --- 1. EXTRACT ---
    console.print("[dim]1. Extracting 3NF relational data from SQLite (OLTP)...[/dim]")
    sqlite_path = "data/raw/pos_transactions.db"
    conn_sqlite = sqlite3.connect(sqlite_path)
    
    df_orders = pl.read_database("SELECT * FROM orders", conn_sqlite)
    df_items = pl.read_database("SELECT * FROM order_items", conn_sqlite)
    df_menu = pl.read_database("SELECT * FROM menu_items", conn_sqlite)
    df_cat = pl.read_database("SELECT * FROM categories", conn_sqlite)
    df_stores = pl.read_database("SELECT * FROM stores", conn_sqlite)
    conn_sqlite.close()

    console.print("[dim]2. Extracting target budget from CSV...[/dim]")
    df_targets = pl.read_csv("data/raw/branch_targets.csv")

    # --- 2. TRANSFORM (Data Hygiene & Dimensional Modeling) ---
    console.print("[dim]3. Transforming & calculating business metrics (OBT & Marts)...[/dim]")
    
    # Join Menu with Category
    df_menu_enriched = df_menu.join(df_cat, on="category_id", how="left")

    # Join Order Items with Enriched Menu
    df_items_enriched = df_items.join(df_menu_enriched, on="menu_id", how="left")

    # Join with Orders & Stores (Building One Big Table / OBT)
    df_obt = df_items_enriched.join(df_orders, on="order_id", how="left") \\
                              .join(df_stores, on="store_id", how="left")

    # Calculate analytical measures
    df_obt = df_obt.with_columns([
        (pl.col("quantity") * pl.col("unit_price")).round(2).alias("gross_sales"),
        pl.col("discount_amount").fill_null(0.0).alias("discount"),
    ]).with_columns([
        (pl.col("gross_sales") - pl.col("discount")).round(2).alias("net_revenue"),
        (pl.col("quantity") * pl.col("cogs")).round(2).alias("total_cogs")
    ]).with_columns([
        (pl.col("net_revenue") - pl.col("total_cogs")).round(2).alias("gross_profit"),
        pl.col("order_datetime").str.slice(0, 10).alias("order_date"),
        pl.col("order_datetime").str.slice(11, 2).cast(pl.Int32).alias("order_hour")
    ]).with_columns([
        ((pl.col("gross_profit") / pl.col("net_revenue")) * 100).round(2).alias("profit_margin_pct")
    ])

    # Build Mart: Store Performance vs Target
    store_actuals = df_obt.group_by(["store_id", "store_name"]).agg([
        pl.col("order_id").n_unique().alias("actual_orders"),
        pl.col("quantity").sum().alias("actual_volume"),
        pl.col("net_revenue").sum().round(2).alias("actual_revenue"),
        pl.col("gross_profit").sum().round(2).alias("actual_profit")
    ])

    mart_store = store_actuals.join(df_targets, on=["store_id", "store_name"], how="left") \\
                              .with_columns([
                                  ((pl.col("actual_revenue") / pl.col("monthly_target")) * 100).round(2).alias("attainment_pct"),
                                  ((pl.col("actual_profit") / pl.col("actual_revenue")) * 100).round(2).alias("margin_pct")
                              ])

    # Build Mart: Menu Profitability Matrix
    mart_menu = df_obt.group_by(["menu_id", "menu_name", "category_name"]).agg([
        pl.col("quantity").sum().alias("units_sold"),
        pl.col("net_revenue").sum().round(2).alias("net_revenue"),
        pl.col("total_cogs").sum().round(2).alias("total_cogs"),
        pl.col("gross_profit").sum().round(2).alias("gross_profit")
    ]).with_columns([
        ((pl.col("gross_profit") / pl.col("net_revenue")) * 100).round(2).alias("profit_margin_pct")
    ]).sort("gross_profit", descending=True)

    # --- 3. LOAD (Processed Parquet & DuckDB Views) ---
    console.print("[dim]4. Loading analytical marts into Parquet & DuckDB OLAP...[/dim]")
    os.makedirs("data/processed", exist_ok=True)
    df_obt.write_parquet("data/processed/fact_order_details.parquet")
    mart_store.write_parquet("data/processed/mart_store_performance.parquet")
    mart_menu.write_parquet("data/processed/mart_menu_profitability.parquet")

    # Register into DuckDB
    conn_duck = duckdb.connect("data/analytics.duckdb")
    conn_duck.execute("CREATE OR REPLACE TABLE fact_order_details AS SELECT * FROM 'data/processed/fact_order_details.parquet'")
    conn_duck.execute("CREATE OR REPLACE TABLE mart_store_performance AS SELECT * FROM 'data/processed/mart_store_performance.parquet'")
    conn_duck.execute("CREATE OR REPLACE TABLE mart_menu_profitability AS SELECT * FROM 'data/processed/mart_menu_profitability.parquet'")
    conn_duck.close()

    console.print("[bold green][OK] ETL Pipeline Completed Successfully![/bold green]")
    console.print("[dim]Parquet marts created and registered in data/analytics.duckdb[/dim]\\n")

if __name__ == "__main__":
    run_etl()
"""

EVIDENCE_DASHBOARD_MD = """# 🍕 Executive Restaurant & Store Analytics

```sql kpis
select 
  round(sum(net_revenue), 2) as total_net_revenue,
  round(sum(gross_profit), 2) as total_gross_profit,
  sum(quantity) as total_pizzas_sold,
  count(distinct order_id) as total_transactions,
  round((sum(gross_profit) / sum(net_revenue)) * 100, 1) as avg_margin_pct
from read_parquet('data/processed/fact_order_details.parquet')
```

```sql store_attainment
select 
  store_name,
  actual_revenue,
  monthly_target,
  round(attainment_pct, 1) as attainment_pct
from read_parquet('data/processed/mart_store_performance.parquet')
order by actual_revenue desc
```

```sql category_margins
select 
  category_name,
  round(sum(net_revenue), 2) as category_revenue,
  round(sum(gross_profit), 2) as category_profit
from read_parquet('data/processed/fact_order_details.parquet')
group by category_name
order by category_revenue desc
```

```sql top_profit_menu
select 
  menu_name,
  category_name,
  units_sold,
  net_revenue,
  gross_profit,
  round(profit_margin_pct, 1) as margin_pct
from read_parquet('data/processed/mart_menu_profitability.parquet')
order by gross_profit desc
limit 5
```

### High-Level Financial & Operational KPIs

{% big_value data="kpis" value="total_net_revenue" title="Total Net Revenue" fmt="usd" /%}
{% big_value data="kpis" value="total_gross_profit" title="Gross Profit" fmt="usd" /%}
{% big_value data="kpis" value="avg_margin_pct" title="Profit Margin" /%}
{% big_value data="kpis" value="total_transactions" title="Transactions" /%}

---

### Store Revenue vs Monthly Target Budget

{% bar_chart 
  data="store_attainment" 
  x="store_name" 
  y="actual_revenue" 
  title="Actual Revenue by Store Branch ($)"
/%}

---

### Category Performance: Revenue vs Gross Profit

{% bar_chart 
  data="category_margins" 
  x="category_name" 
  y="category_revenue" 
  title="Category Revenue Breakdown ($)"
/%}

---

### Top 5 Most Profitable Menu Items

{% table 
  data="top_profit_menu" 
/%}
"""

MARP_PRESENTATION_MD = """---
marp: true
theme: default
paginate: true
header: "🍕 Restaurant Performance | Executive Readout"
footer: "Confidential - For Leadership Team"
style: |
  section {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    padding: 40px;
  }
  h1 { color: #991b1b; }
  h2 { color: #0f172a; }
  .highlight { color: #16a34a; font-weight: bold; }
---

# 🍕 Executive Store & Product Performance Review
### Multi-Branch Revenue, Profit Margins & Target Attainment
**Prepared by:** Lead Data Analyst  
**Context:** OLTP Store POS Ingestion & Analytical Review

---

## 1. Executive Summary & Topline Financials

* **Total Net Revenue:** **$567.50** (after promotional discounts).
* **Total Gross Profit:** **$362.00** achieving a healthy **63.8% Gross Margin**.
* **Order Velocity:** **20 transactions** across 3 regional branches.
* **Core Takeaway:** Revenue is healthy, but branch attainment varies significantly across suburban vs downtown locations.

---

## 2. Store Branch Target Attainment

| Branch | Actual Revenue | Monthly Target | Attainment % | Profit Margin |
| :--- | :--- | :--- | :--- | :--- |
| **Downtown Flagship** | $278.50 | $600.00 | **46.4%** | **64.2%** |
| **Uptown Mall** | $174.00 | $450.00 | **38.7%** | **63.5%** |
| **Suburban Express** | $115.00 | $300.00 | **38.3%** | **63.0%** |

*Downtown Flagship leads in volume and maintains the highest profit margin.*

---

## 3. Menu Profitability Matrix (Stars vs Low-Margin)

1. **The Meat Lovers (Supreme):** #1 Profit Driver ($112.00 Gross Profit, 67% margin).
2. **The BBQ Chicken Pizza (Chicken):** #2 Profit Driver ($88.00 Gross Profit, 64% margin).
3. **The Pepperoni Pizza (Classic):** Consistent volume driver ($72.00 Gross Profit).
4. **The Margherita (Veggie):** Lower dollar profit, but consistent vegetarian staple.

---

## 4. Strategic Recommendations for Leadership

* **Marketing & Channel Focus:**
  * Double down on Downtown Flagship dinner promos (highest margin leverage).
  * Introduce combo bundling in Suburban Express to lift ticket size toward target.
* **Menu Engineering:**
  * Feature **Meat Lovers & BBQ Chicken** prominently on digital delivery menus.
* **Operational Next Steps:**
  * Automated weekly ETL sync from SQLite store POS to analytical DuckDB mart.
"""

def init_sqlite_pos_database(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE stores (
        store_id INTEGER PRIMARY KEY,
        store_name TEXT,
        city TEXT,
        store_type TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE categories (
        category_id INTEGER PRIMARY KEY,
        category_name TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE menu_items (
        menu_id INTEGER PRIMARY KEY,
        menu_name TEXT,
        category_id INTEGER,
        unit_price REAL,
        cogs REAL
    );
    """)

    cur.execute("""
    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        order_datetime TEXT,
        store_id INTEGER,
        customer_id INTEGER,
        payment_method TEXT,
        order_status TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE order_items (
        item_id INTEGER PRIMARY KEY,
        order_id INTEGER,
        menu_id INTEGER,
        quantity INTEGER,
        discount_amount REAL
    );
    """)

    # Insert Stores
    stores_data = [
        (1, "Downtown Flagship", "Jakarta Pusat", "Dine-In & Takeout"),
        (2, "Uptown Mall", "Jakarta Selatan", "Mall Outlet"),
        (3, "Suburban Express", "Tangerang", "Delivery Only")
    ]
    cur.executemany("INSERT INTO stores VALUES (?, ?, ?, ?)", stores_data)

    # Insert Categories
    cat_data = [
        (1, "Classic"),
        (2, "Supreme"),
        (3, "Chicken"),
        (4, "Veggie")
    ]
    cur.executemany("INSERT INTO categories VALUES (?, ?)", cat_data)

    # Insert Menu Items (price and cogs)
    menu_data = [
        (101, "The Pepperoni Pizza", 1, 19.50, 6.50),
        (102, "The Hawaiian Pizza", 1, 17.00, 5.50),
        (201, "The Meat Lovers", 2, 22.00, 7.00),
        (202, "The Spicy Supreme", 2, 18.50, 6.00),
        (301, "The BBQ Chicken Pizza", 3, 20.00, 6.50),
        (302, "The Buffalo Chicken", 3, 18.00, 6.00),
        (401, "The Margherita", 4, 14.50, 4.00),
        (402, "The Four Cheese", 4, 16.00, 5.00)
    ]
    cur.executemany("INSERT INTO menu_items VALUES (?, ?, ?, ?, ?)", menu_data)

    # Insert Orders
    orders_data = [
        (1001, "2026-09-01 11:32:00", 1, 501, "Credit Card", "Completed"),
        (1002, "2026-09-01 12:05:00", 1, 502, "Cash", "Completed"),
        (1003, "2026-09-01 12:15:00", 2, 503, "Digital Wallet", "Completed"),
        (1004, "2026-09-01 12:45:00", 1, 504, "Credit Card", "Completed"),
        (1005, "2026-09-01 13:10:00", 3, 505, "Cash", "Completed"),
        (1006, "2026-09-01 18:20:00", 1, 506, "Credit Card", "Completed"),
        (1007, "2026-09-01 18:45:00", 2, 507, "Digital Wallet", "Completed"),
        (1008, "2026-09-01 19:15:00", 3, 508, "Cash", "Completed"),
        (1009, "2026-09-02 11:50:00", 1, 509, "Credit Card", "Completed"),
        (1010, "2026-09-02 12:20:00", 2, 510, "Digital Wallet", "Completed"),
        (1011, "2026-09-02 12:35:00", 3, 511, "Cash", "Completed"),
        (1012, "2026-09-02 13:00:00", 1, 512, "Credit Card", "Completed"),
        (1013, "2026-09-02 18:30:00", 2, 513, "Credit Card", "Completed"),
        (1014, "2026-09-02 19:00:00", 1, 514, "Cash", "Completed"),
        (1015, "2026-09-02 19:40:00", 3, 515, "Digital Wallet", "Completed"),
        (1016, "2026-09-03 12:10:00", 1, 516, "Credit Card", "Completed"),
        (1017, "2026-09-03 12:40:00", 2, 517, "Digital Wallet", "Completed"),
        (1018, "2026-09-03 18:15:00", 1, 518, "Credit Card", "Completed"),
        (1019, "2026-09-03 19:25:00", 3, 519, "Cash", "Completed"),
        (1020, "2026-09-03 20:10:00", 2, 520, "Digital Wallet", "Completed")
    ]
    cur.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)", orders_data)

    # Insert Order Items (with occasional discounts)
    items_data = [
        (1, 1001, 101, 2, 2.00),
        (2, 1002, 202, 1, 0.00),
        (3, 1003, 401, 1, 0.00),
        (4, 1004, 301, 3, 5.00),
        (5, 1005, 102, 2, 0.00),
        (6, 1006, 201, 2, 2.00),
        (7, 1007, 302, 1, 0.00),
        (8, 1008, 402, 2, 1.00),
        (9, 1009, 101, 1, 0.00),
        (10, 1010, 301, 2, 2.00),
        (11, 1011, 401, 1, 0.00),
        (12, 1012, 202, 1, 0.00),
        (13, 1013, 101, 2, 0.00),
        (14, 1014, 201, 2, 3.00),
        (15, 1015, 401, 1, 0.00),
        (16, 1016, 301, 1, 0.00),
        (17, 1017, 102, 2, 1.00),
        (18, 1018, 201, 3, 4.00),
        (19, 1019, 101, 2, 0.00),
        (20, 1020, 302, 1, 0.00)
    ]
    cur.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?)", items_data)

    conn.commit()
    conn.close()

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

    # 1. Initialize SQLite OLTP Database
    sqlite_db_path = os.path.join(target_dir, "data", "raw", "pos_transactions.db")
    init_sqlite_pos_database(sqlite_db_path)

    # 2. Write CSV Targets
    targets_csv_path = os.path.join(target_dir, "data", "raw", "branch_targets.csv")
    with open(targets_csv_path, "w", encoding="utf-8") as f:
        f.write(BRANCH_TARGETS_CSV.strip() + "\n")

    # 3. Write Data Dictionary & SQL Models
    dict_path = os.path.join(target_dir, "models", "data_dictionary.md")
    with open(dict_path, "w", encoding="utf-8") as f:
        f.write(DATA_DICTIONARY_MD.strip() + "\n")

    sql_path = os.path.join(target_dir, "models", "marts.sql")
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write(SQL_MODELS_CONTENT.strip() + "\n")

    # 4. Write ETL Pipeline Script
    etl_path = os.path.join(target_dir, "etl.py")
    with open(etl_path, "w", encoding="utf-8") as f:
        f.write(ETL_PIPELINE_SCRIPT.strip() + "\n")

    # 5. Scaffold Evidence Dashboard inside reports/
    reports_dir = os.path.join(target_dir, "reports")
    evidence_cli = shutil.which("evidence") or shutil.which("evd")
    if evidence_cli:
        try:
            subprocess.run([evidence_cli, "init", reports_dir], capture_output=True, shell=True)
        except Exception:
            os.makedirs(os.path.join(reports_dir, "pages"), exist_ok=True)
    else:
        os.makedirs(os.path.join(reports_dir, "pages"), exist_ok=True)

    pages_dir = os.path.join(reports_dir, "pages")
    os.makedirs(pages_dir, exist_ok=True)
    with open(os.path.join(pages_dir, "home.md"), "w", encoding="utf-8") as f:
        f.write(EVIDENCE_DASHBOARD_MD.strip() + "\n")

    # 6. Write Marp Presentation Deck
    marp_path = os.path.join(target_dir, "slides", "presentation.md")
    with open(marp_path, "w", encoding="utf-8") as f:
        f.write(MARP_PRESENTATION_MD.strip() + "\n")

    # 7. Write Comprehensive README
    readme_content = f"""# {project_name}

Data analysis project scaffolded with the **Data Analyst Workbench**.

## Architecture & Data Flow
1. **OLTP Source:** `data/raw/pos_transactions.db` (Normalized SQLite: stores, categories, menu_items, orders, order_items).
2. **Targets Ingestion:** `data/raw/branch_targets.csv` (Branch monthly targets).
3. **ETL Transformation:** `etl.py` (Polars + DuckDB) extracts OLTP, normalizes, calculates margins, and builds OLAP Marts.
4. **OLAP Storage:** `data/processed/*.parquet` and registered views in `data/analytics.duckdb`.
5. **Interactive Dashboard:** `reports/` (Evidence.dev) for operations and branch managers.
6. **Executive Presentation:** `slides/presentation.md` (Marp) for C-Level readouts.

## Quick Commands
```powershell
# 1. Run the ETL Pipeline (OLTP SQLite -> OLAP DuckDB)
analyst run

# 2. Inspect Raw Data / Targets
analyst inspect data/raw/pos_transactions.db
analyst stats data/raw/branch_targets.csv

# 3. Query Analytical Marts
analyst query models/marts.sql

# 4. Launch BI Dashboard
analyst dashboard

# 5. Compile Executive Slides
analyst slides --format html
```
"""
    with open(os.path.join(target_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)

    console.print(f"[bold green][OK] Project '{os.path.basename(target_dir)}' successfully created![/bold green]")
    console.print(f"[cyan]Next step:[/cyan] [yellow]cd \"{target_dir}\"[/yellow]")
    console.print("[dim]Run 'analyst run' to execute the OLTP -> OLAP ETL pipeline.[/dim]\n")
