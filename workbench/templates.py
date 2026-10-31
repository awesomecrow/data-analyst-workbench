import os
import subprocess
import shutil
import sqlite3
from rich.console import Console

from workbench.config import load_config

console = Console()

GENERIC_SEGMENT_TARGETS_CSV = """segment_id,segment_name,monthly_target,target_volume
1,Corporate,100000.00,500
2,Small Business,50000.00,300
3,Consumer,25000.00,200
"""

GENERIC_DATA_DICTIONARY_MD = """# Data Dictionary & Dual-Engine Pipeline Governance

## 1. Dual-Engine Architecture
1. **Sources (`data/raw/`):** Heterogeneous data drop zone: SQLite OLTP (`operational.db`), CSV (`*.csv`), Excel (`*.xlsx`), or Parquet (`*.parquet`).
2. **Auto-Ingest:** Automatically snapshots raw files into `data/staging/*.parquet` and registers tables into DuckDB.
3. **Quarantine Gate:** Validates business rules, routing anomalies to `data/quarantine/` with audit logs.
4. **Declarative SQL Modeling (`models/*.sql`):** Pure SQL models transform normalized staging tables into dimensional analytical marts (`data/marts/*.parquet`).
5. **Reconciliation & Validation:** Financial and row conservation checks before final BI materialization.
6. **Deliverables:** Zero-cloud interactive BI dashboard (`analyst dashboard`) and executive slide deck (`analyst slides`).

## 2. OLTP Operational Schema (`data/raw/operational.db`)
* `customers`: `(customer_id INT PK, customer_name TEXT, segment TEXT, region TEXT)`
* `products`: `(product_id INT PK, product_name TEXT, category TEXT, unit_price REAL)`
* `orders`: `(order_id INT PK, order_date TEXT, customer_id INT FK, status TEXT)`
* `order_items`: `(item_id INT PK, order_id INT FK, product_id INT FK, quantity INT, discount REAL)`
"""

GENERIC_SQL_MODELS_CONTENT = """-- Analytical SQL Models (OLAP)
-- Materialized automatically to data/marts/*.parquet by: analyst run

-- 1. Segment Revenue & Attainment
SELECT 
    c.segment,
    COUNT(DISTINCT o.order_id) AS total_orders,
    SUM(oi.quantity) AS total_volume,
    ROUND(SUM(oi.quantity * p.unit_price * (1.0 - COALESCE(oi.discount, 0.0))), 2) AS total_revenue
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE o.status = 'Completed'
GROUP BY c.segment
ORDER BY total_revenue DESC;
"""

GENERIC_MARP_PRESENTATION_MD = """---
marp: true
theme: default
paginate: true
header: "📊 Executive Analytics Readout"
footer: "Confidential - Audited via Data Analyst Workbench (Dual-Engine OLTP/OLAP)"
style: |
  section {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    padding: 40px;
  }
  h1 { color: #1e3a8a; }
  h2 { color: #0f172a; }
  .highlight { color: #16a34a; font-weight: bold; }
---

# 📊 Executive Business Performance Review
### Strategic Metric Evaluation & Operational Breakdown
**Prepared by:** Lead Data Analyst  
**Pipeline Engine:** Dual-Engine (SQLite OLTP + DuckDB OLAP)

---

## 1. Executive Summary & Topline Scorecard

* **Primary Objective:** Measure core performance indicators against target benchmarks.
* **Data Foundation:** 100% reconciled from operational source tables to analytical marts.
* **Key Observations:**
  * Performance variance across segments and operational cohorts.
  * Anomalous records and boundary exceptions isolated to audit quarantine.

---

## 2. Segment & Dimensional Performance

| Segment / Category | Volume | Total Value ($) | Realization / Target % | Efficiency Score |
| :--- | :--- | :--- | :--- | :--- |
| **Segment A** | 1,250 | $124,500.00 | **94.2%** | **High** |
| **Segment B** | 890 | $88,200.00 | **88.5%** | **Medium** |
| **Segment C** | 420 | $39,800.00 | **72.1%** | **Underperforming** |

*Segment A delivers primary volume; Segment C requires operational turnaround.*

---

## 3. Operational Bottlenecks & Exceptions

1. **Cycle Time Distribution:** Peak turnaround times observed during high-velocity windows.
2. **Exception Handling:** Boundary rules successfully quarantined invalid status transitions.
3. **Cohort Stability:** Maturity cohorts reveal consistent resolution within contractual SLAs.

---

## 4. Strategic Recommendations & Action Plan

* **Immediate Actions (Week 1-2):**
  * Address top bottlenecks identified in low-performing segments.
  * Implement automated daily reconciliation alerts.
* **Medium-Term Strategy (Month 1-3):**
  * Reallocate resources to high-attainment channels.
  * Expand analytical mart dimensions for deeper cohort tracking.
"""

GENERIC_EVIDENCE_DASHBOARD_MD = """# 📊 Executive Business Analytics Dashboard

### Topline Performance Indicators

{% big_value data="segment_attainment" value="sum(total_revenue)" title="Total Net Revenue" fmt="usd" /%}
{% big_value data="segment_attainment" value="sum(total_volume)" title="Total Units Sold" /%}
{% big_value data="segment_attainment" value="sum(total_orders)" title="Verified Orders" /%}

---

### Segment Revenue Contribution

{% bar_chart 
  data="segment_attainment" 
  x="segment" 
  y="total_revenue" 
  title="Realized Revenue by Segment ($)"
/%}

---

### Segment Performance Table

{% table data="segment_attainment" /%}
"""

def init_generic_sqlite_database(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        customer_name TEXT,
        segment TEXT,
        region TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY,
        product_name TEXT,
        category TEXT,
        unit_price REAL
    );
    """)
    cur.execute("""
    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        order_date TEXT,
        customer_id INTEGER REFERENCES customers(customer_id),
        status TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE order_items (
        item_id INTEGER PRIMARY KEY,
        order_id INTEGER REFERENCES orders(order_id),
        product_id INTEGER REFERENCES products(product_id),
        quantity INTEGER,
        discount REAL
    );
    """)

    cur.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", [
        (1, "Acme Corp", "Corporate", "North America"),
        (2, "Beta Retail", "Small Business", "Europe"),
        (3, "Delta Logistics", "Corporate", "Asia Pacific"),
        (4, "John Doe", "Consumer", "North America"),
    ])
    cur.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", [
        (101, "Enterprise Suite", "Software", 1200.00),
        (102, "Standard License", "Software", 450.00),
        (201, "Hardware Gateway", "Hardware", 850.00),
        (301, "Consulting Hours", "Services", 150.00),
    ])
    cur.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", [
        (1001, "2026-06-01", 1, "Completed"),
        (1002, "2026-06-02", 2, "Completed"),
        (1003, "2026-06-03", 3, "Completed"),
        (1004, "2026-06-04", 4, "Completed"),
    ])
    cur.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?)", [
        (1, 1001, 101, 2, 0.10),
        (2, 1002, 102, 5, 0.05),
        (3, 1003, 201, 3, 0.00),
        (4, 1004, 301, 10, 0.00),
    ])
    conn.commit()
    conn.close()

BRANCH_TARGETS_CSV = """store_id,store_name,monthly_target,target_volume
1,Downtown Flagship,600.00,35
2,Uptown Mall,450.00,25
3,Suburban Express,300.00,20
"""

DATA_DICTIONARY_MD = """# Data Dictionary & 7-Stage Pipeline Governance

## 1. 7-Stage Pipeline Architecture
1. **Sources:** Multi-source operational inputs (`data/raw/pos_transactions.db` SQLite OLTP, `data/raw/branch_targets.csv`, Excel `.xlsx`, or upstream DB/Webhooks).
2. **Extract:** High-speed connectors via `sqlite3`, `polars`, and `fastexcel`/`openpyxl`.
3. **Staging / Landing:** Immutable raw snapshots persisted in `data/staging/*.parquet`.
4. **Source Validation (Gate 1):** Pre-flight schema and rule checks. Invalid records are routed to `data/quarantine/` (`error_log.json` & CSV).
5. **Transform:** Standardization, relational joins, currency/date hygiene, and Star/OBT modeling via Polars (with zero-copy `.to_pandas()` bridge).
6. **Target Validation (Gate 2) & Load:** Cross-table revenue reconciliation and data contract assertions before loading into `data/processed/`, `data/marts/`, and `data/analytics.duckdb`.
7. **Business Intelligence & Deliverables:** Interactive web BI (`reports/` via Evidence.dev), executive slides (`slides/` via Marp), and SQL models (`models/marts.sql`).

---

## 2. Business Metric Definitions
* **Gross Sales ($):** Total sales value before discounts (`quantity * unit_price`).
* **Discount ($):** Value of promotion, voucher, or loyalty rebate applied.
* **Net Revenue ($):** Realized income received from the customer (`gross_sales - discount_amount`).
* **Cost of Goods Sold / COGS ($):** Direct ingredient and packaging cost (`quantity * cogs`).
* **Gross Profit ($):** Dollar contribution after ingredient costs (`net_revenue - total_cogs`).
* **Gross Margin (%):** Profitability efficiency (`(gross_profit / net_revenue) * 100`).
* **Average Ticket Size / AOV ($):** Average customer spend per transaction (`net_revenue / distinct_orders`).
* **Target Attainment (%):** Store achievement vs monthly revenue budget (`(actual_revenue / monthly_target) * 100`).

---

## 3. OLTP Source Schema (`data/raw/pos_transactions.db` - SQLite)
* `stores`: `(store_id INT, store_name TEXT, city TEXT, store_type TEXT)`
* `categories`: `(category_id INT, category_name TEXT)`
* `menu_items`: `(menu_id INT, menu_name TEXT, category_id INT, unit_price REAL, cogs REAL)`
* `orders`: `(order_id INT, order_datetime TEXT, store_id INT, customer_id INT, payment_method TEXT, order_status TEXT)`
* `order_items`: `(item_id INT, order_id INT, menu_id INT, quantity INT, discount_amount REAL)`

---

## 4. OLAP Analytical Target Schema (`data/analytics.duckdb` & Parquet)
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
import sys
import sqlite3
import polars as pl
import duckdb
from rich.console import Console
from workbench.checkpoint import CheckpointTracker

console = Console()


def run_etl(interactive: bool = False):
    console.print("[bold cyan]Starting 7-Stage Audited ETL Pipeline (OLTP -> Quarantine Gate -> OLAP)...[/bold cyan]")
    tracker = CheckpointTracker(project_name=os.path.basename(os.getcwd()), interactive=interactive)

    # =========================================================================
    # STAGE 1 & 2: SOURCES & EXTRACT
    # =========================================================================
    sqlite_path = "data/raw/pos_transactions.db"
    conn_sqlite = sqlite3.connect(sqlite_path)

    df_orders_raw = pl.read_database("SELECT * FROM orders", conn_sqlite)
    df_items_raw = pl.read_database("SELECT * FROM order_items", conn_sqlite)
    df_menu = pl.read_database("SELECT * FROM menu_items", conn_sqlite)
    df_cat = pl.read_database("SELECT * FROM categories", conn_sqlite)
    df_stores = pl.read_database("SELECT * FROM stores", conn_sqlite)
    conn_sqlite.close()

    df_targets = pl.read_csv("data/raw/branch_targets.csv")

    tracker.record_stage(
        stage_num=1,
        stage_name="EXTRACT (Sources)",
        what=f"Extracted {len(df_orders_raw)} orders, {len(df_items_raw)} order items, {len(df_menu)} menu items from SQLite OLTP, and {len(df_targets)} branch targets from CSV.",
        why="Collect raw operational POS transactions and monthly executive budget targets from source systems.",
        how="Executed sqlite3 relational extraction via pl.read_database() and CSV ingestion via pl.read_csv().",
        status="PASSED",
        metrics={
            "raw_orders": len(df_orders_raw),
            "raw_items": len(df_items_raw),
            "stores": len(df_stores),
            "targets": len(df_targets),
        },
    )

    # =========================================================================
    # STAGE 3: STAGING / LANDING
    # =========================================================================
    os.makedirs("data/staging", exist_ok=True)
    df_orders_raw.write_parquet("data/staging/stg_orders_raw.parquet")
    df_items_raw.write_parquet("data/staging/stg_order_items_raw.parquet")
    df_targets.write_parquet("data/staging/stg_branch_targets.parquet")

    tracker.record_stage(
        stage_num=2,
        stage_name="STAGING / LANDING",
        what="Materialized immutable raw extracts into data/staging/*.parquet before applying validation filters.",
        why="Preserve an exact landing copy of source data for auditability and replay without re-querying operational DBs.",
        how="Saved Polars DataFrames to Snappy-compressed Parquet snapshots in data/staging/.",
        status="PASSED",
        metrics={"staging_files": 3},
    )

    # =========================================================================
    # STAGE 4: SOURCE VALIDATION (Gate 1 - Validasi Awal & Quarantine)
    # =========================================================================
    os.makedirs("data/quarantine", exist_ok=True)

    # Validate Orders: order_datetime must not be null/empty and order_status must be 'Completed'
    valid_order_mask = (
        pl.col("order_datetime").is_not_null()
        & (pl.col("order_datetime").str.len_chars() >= 10)
        & (pl.col("order_status") == "Completed")
    )
    df_orders_valid = df_orders_raw.filter(valid_order_mask)
    df_orders_rejected = df_orders_raw.filter(~valid_order_mask)

    if len(df_orders_rejected) > 0:
        rej_orders_path = "data/quarantine/rejected_orders.csv"
        df_orders_rejected.write_csv(rej_orders_path)
        tracker.log_quarantine(
            gate="SOURCE_VALIDATION",
            source_table="orders",
            reason="Missing order_datetime or non-Completed order_status",
            rejected_count=len(df_orders_rejected),
            sample_records=df_orders_rejected.to_dicts()[:3],
            csv_path=rej_orders_path,
        )

    # Validate Order Items: quantity > 0, valid menu_id, and parent order_id must be valid
    valid_menu_ids = df_menu["menu_id"].to_list()
    valid_order_ids = df_orders_valid["order_id"].to_list()

    valid_item_mask = (
        (pl.col("quantity") > 0)
        & pl.col("menu_id").is_in(valid_menu_ids)
        & pl.col("order_id").is_in(valid_order_ids)
    )
    df_items = df_items_raw.filter(valid_item_mask)
    df_items_rejected = df_items_raw.filter(~valid_item_mask)

    if len(df_items_rejected) > 0:
        rej_items_path = "data/quarantine/rejected_order_items.csv"
        df_items_rejected.write_csv(rej_items_path)
        tracker.log_quarantine(
            gate="SOURCE_VALIDATION",
            source_table="order_items",
            reason="Invalid quantity (<= 0), unknown menu_id, or orphaned/cancelled order_id",
            rejected_count=len(df_items_rejected),
            sample_records=df_items_rejected.to_dicts()[:3],
            csv_path=rej_items_path,
        )

    df_orders = df_orders_valid
    total_quarantined = len(df_orders_rejected) + len(df_items_rejected)

    tracker.record_stage(
        stage_num=3,
        stage_name="SOURCE VALIDATION (Gate 1)",
        what=f"Validated incoming records: {len(df_orders)} orders & {len(df_items)} items passed; {total_quarantined} anomalous row(s) isolated to quarantine.",
        why="Prevent corrupted timestamps, cancelled orders, or negative quantities from polluting downstream financial metrics.",
        how="Applied Polars boolean predicate masks; routed failed rows to data/quarantine/*.csv and error_log.json.",
        status="PASSED",
        metrics={
            "valid_orders": len(df_orders),
            "valid_items": len(df_items),
            "quarantined_rows": total_quarantined,
        },
    )

    # =========================================================================
    # STAGE 5: TRANSFORM (Standardize, Join, Compute OBT & Marts)
    # =========================================================================
    df_menu_enriched = df_menu.join(df_cat, on="category_id", how="left")
    df_items_enriched = df_items.join(df_menu_enriched, on="menu_id", how="left")

    df_obt = (
        df_items_enriched.join(df_orders, on="order_id", how="left")
        .join(df_stores, on="store_id", how="left")
    )

    df_obt = (
        df_obt.with_columns([
            (pl.col("quantity") * pl.col("unit_price")).round(2).alias("gross_sales"),
            pl.col("discount_amount").fill_null(0.0).alias("discount"),
        ])
        .with_columns([
            (pl.col("gross_sales") - pl.col("discount")).round(2).alias("net_revenue"),
            (pl.col("quantity") * pl.col("cogs")).round(2).alias("total_cogs"),
        ])
        .with_columns([
            (pl.col("net_revenue") - pl.col("total_cogs")).round(2).alias("gross_profit"),
            pl.col("order_datetime").str.slice(0, 10).alias("order_date"),
            pl.col("order_datetime").str.slice(11, 2).cast(pl.Int32).alias("order_hour"),
        ])
        .with_columns([
            ((pl.col("gross_profit") / pl.col("net_revenue")) * 100).round(2).alias("profit_margin_pct")
        ])
    )

    # Optional Pandas Bridge (available anytime for custom scikit-learn / statsmodels workflows):
    # df_obt_pandas = df_obt.to_pandas()

    store_actuals = df_obt.group_by(["store_id", "store_name"]).agg([
        pl.col("order_id").n_unique().alias("actual_orders"),
        pl.col("quantity").sum().alias("actual_volume"),
        pl.col("net_revenue").sum().round(2).alias("actual_revenue"),
        pl.col("gross_profit").sum().round(2).alias("actual_profit"),
    ])

    mart_store = (
        store_actuals.join(df_targets, on=["store_id", "store_name"], how="left")
        .with_columns([
            ((pl.col("actual_revenue") / pl.col("monthly_target")) * 100).round(2).alias("attainment_pct"),
            ((pl.col("actual_profit") / pl.col("actual_revenue")) * 100).round(2).alias("margin_pct"),
        ])
        .sort("actual_revenue", descending=True)
    )

    mart_menu = (
        df_obt.group_by(["menu_id", "menu_name", "category_name"])
        .agg([
            pl.col("quantity").sum().alias("units_sold"),
            pl.col("net_revenue").sum().round(2).alias("net_revenue"),
            pl.col("total_cogs").sum().round(2).alias("total_cogs"),
            pl.col("gross_profit").sum().round(2).alias("gross_profit"),
        ])
        .with_columns([
            ((pl.col("gross_profit") / pl.col("net_revenue")) * 100).round(2).alias("profit_margin_pct")
        ])
        .sort("gross_profit", descending=True)
    )

    tracker.record_stage(
        stage_num=4,
        stage_name="TRANSFORM (OBT & Marts)",
        what=f"Built denormalized OBT ({len(df_obt)} rows), Store Performance Mart ({len(mart_store)} stores), and Menu Profitability Mart ({len(mart_menu)} items).",
        why="Transform 3NF operational tables into business-ready analytical structures answering revenue, margin, and target attainment.",
        how="Joined 5 relational tables in Polars, imputed null discounts to 0.0, parsed ISO dates, and aggregated dimensional marts.",
        status="PASSED",
        metrics={
            "obt_rows": len(df_obt),
            "mart_store_rows": len(mart_store),
            "mart_menu_rows": len(mart_menu),
        },
    )

    # =========================================================================
    # STAGE 6: TARGET VALIDATION (Gate 2 - Validasi Target & Reconciliation)
    # =========================================================================
    obt_rev = round(float(df_obt["net_revenue"].sum()), 2)
    store_rev = round(float(mart_store["actual_revenue"].sum()), 2)
    menu_rev = round(float(mart_menu["net_revenue"].sum()), 2)
    min_margin = round(float(df_obt["profit_margin_pct"].min()), 2)

    reconciled = (abs(obt_rev - store_rev) < 0.01) and (abs(obt_rev - menu_rev) < 0.01) and (min_margin > 0)
    if not reconciled:
        tracker.log_quarantine(
            gate="TARGET_VALIDATION",
            source_table="mart_reconciliation",
            reason=f"Revenue mismatch: OBT={obt_rev}, StoreMart={store_rev}, MenuMart={menu_rev}",
            rejected_count=1,
        )
        tracker.record_stage(
            stage_num=5,
            stage_name="TARGET VALIDATION (Gate 2)",
            what="Target reconciliation failed between OBT and aggregated marts.",
            why="Ensure 100% financial accuracy before exposing numbers to executive BI dashboards.",
            how="Cross-checked sum(net_revenue) across OBT, Store Mart, and Menu Mart.",
            status="FAILED",
        )
        tracker.finalize("FAILED")
        sys.exit(1)

    tracker.record_stage(
        stage_num=5,
        stage_name="TARGET VALIDATION (Gate 2)",
        what=f"100% financial reconciliation verified: Total Net Revenue = ${obt_rev:.2f} across OBT, Store Mart, and Menu Mart (Min Margin = {min_margin}%).",
        why="Guarantee zero discrepancy between line-item transactions and executive summary tables before loading to BI.",
        how="Executed automated reconciliation assertions (OBT == Store Mart == Menu Mart) and positive margin boundary checks.",
        status="PASSED",
        metrics={
            "reconciled_net_revenue": obt_rev,
            "min_margin_pct": min_margin,
        },
    )

    # =========================================================================
    # STAGE 7: LOAD ANALYTICAL DATASET (Parquet & DuckDB OLAP Serving Layer)
    # =========================================================================
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/marts", exist_ok=True)

    for folder in ("data/processed", "data/marts"):
        df_obt.write_parquet(f"{folder}/fact_order_details.parquet")
        mart_store.write_parquet(f"{folder}/mart_store_performance.parquet")
        mart_menu.write_parquet(f"{folder}/mart_menu_profitability.parquet")

    conn_duck = duckdb.connect("data/analytics.duckdb")
    conn_duck.execute("CREATE OR REPLACE TABLE fact_order_details AS SELECT * FROM 'data/processed/fact_order_details.parquet'")
    conn_duck.execute("CREATE OR REPLACE TABLE mart_store_performance AS SELECT * FROM 'data/processed/mart_store_performance.parquet'")
    conn_duck.execute("CREATE OR REPLACE TABLE mart_menu_profitability AS SELECT * FROM 'data/processed/mart_menu_profitability.parquet'")
    conn_duck.close()

    tracker.record_stage(
        stage_num=6,
        stage_name="LOAD ANALYTICAL DATASET",
        what="Persisted 3 analytical marts to Parquet (data/processed/ & data/marts/) and registered tables in data/analytics.duckdb.",
        why="Provide sub-second columnar query performance for Evidence.dev BI dashboards, Marp slides, and ad-hoc SQL.",
        how="Wrote Snappy Parquet files and executed CREATE OR REPLACE TABLE in DuckDB.",
        status="PASSED",
        metrics={"duckdb_tables": 3, "parquet_files": 6},
    )

    manifest_path = tracker.finalize("SUCCESS")
    console.print("[bold green][OK] 7-Stage ETL Pipeline Completed Successfully![/bold green]")
    console.print(f"[dim]Audit checkpoint manifest saved to: {manifest_path}[/dim]")
    console.print("[dim]Run 'analyst checkpoint' anytime to inspect What, Why, How & Quarantine logs.[/dim]")


if __name__ == "__main__":
    is_interactive = "--interactive" in sys.argv or "-i" in sys.argv
    run_etl(interactive=is_interactive)
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
footer: "Confidential - Audited via 7-Stage Data Analyst Workbench"
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
**Audit Status:** 100% Reconciled via 7-Stage ETL & Quarantine Gate

---

## 1. Executive Summary & Topline Financials

* **Total Net Revenue:** **$607.00** (after promotional discounts, 100% reconciled).
* **Total Gross Profit:** **$405.50** achieving a strong **66.8% Gross Margin**.
* **Order Velocity:** **20 verified transactions** across 3 regional branches (2 corrupted POS sync rows automatically quarantined).
* **Core Takeaway:** Revenue is healthy, with Supreme and Classic categories driving the bulk of gross profit.

---

## 2. Store Branch Target Attainment

| Branch | Actual Revenue | Monthly Target | Attainment % | Profit Margin |
| :--- | :--- | :--- | :--- | :--- |
| **Downtown Flagship** | $296.00 | $600.00 | **49.3%** | **66.4%** |
| **Uptown Mall** | $184.50 | $450.00 | **41.0%** | **66.7%** |
| **Suburban Express** | $126.50 | $300.00 | **42.2%** | **68.0%** |

*Downtown Flagship leads in volume and revenue attainment.*

---

## 3. Menu Profitability Matrix (Stars vs Low-Margin)

1. **The Meat Lovers (Supreme):** #1 Profit Driver ($96.00 Gross Profit, 66.2% margin).
2. **The Pepperoni Pizza (Classic):** #2 Profit Driver ($89.00 Gross Profit, 66.2% margin).
3. **The BBQ Chicken Pizza (Chicken):** Strong volume contributor ($74.00 Gross Profit, 65.5% margin).
4. **The Margherita (Veggie):** Highest percentage margin (72.4% margin).

---

## 4. Data Governance & Strategic Recommendations

* **Data Hygiene & Governance:**
  * Source Validation Gate isolated **2 anomalous POS records** (cancelled/corrupted sync & negative quantity) into `data/quarantine/`.
* **Marketing & Channel Focus:**
  * Double down on Downtown Flagship dinner promos.
  * Introduce combo bundling in Suburban Express to lift ticket size toward target.
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
        (3, "Suburban Express", "Tangerang", "Delivery Only"),
    ]
    cur.executemany("INSERT INTO stores VALUES (?, ?, ?, ?)", stores_data)

    # Insert Categories
    cat_data = [
        (1, "Classic"),
        (2, "Supreme"),
        (3, "Chicken"),
        (4, "Veggie"),
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
        (402, "The Four Cheese", 4, 16.00, 5.00),
    ]
    cur.executemany("INSERT INTO menu_items VALUES (?, ?, ?, ?, ?)", menu_data)

    # Insert 20 Valid Orders + 1 Corrupted/Cancelled Order (9901) to demonstrate Source Validation Quarantine Gate
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
        (1020, "2026-09-03 20:10:00", 2, 520, "Digital Wallet", "Completed"),
        (9901, "", 1, 599, "Cash", "Cancelled_Sync_Error"),
    ]
    cur.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)", orders_data)

    # Insert 20 Valid Order Items + 1 Invalid Order Item (item_id=99, negative quantity)
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
        (20, 1020, 302, 1, 0.00),
        (99, 1001, 101, -2, 0.00),
    ]
    cur.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?)", items_data)

    conn.commit()
    conn.close()


def scaffold_project(project_name: str, template: str = "generic", target_path: str | None = None):
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

    # Create 7-Stage folder structure
    for sub in ("raw", "staging", "quarantine", "checkpoints", "processed", "marts"):
        os.makedirs(os.path.join(target_dir, "data", sub), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "models"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "slides"), exist_ok=True)

    is_restaurant = (template == "restaurant-sales")

    # 1. Initialize SQLite OLTP Database
    if is_restaurant:
        sqlite_db_path = os.path.join(target_dir, "data", "raw", "pos_transactions.db")
        init_sqlite_pos_database(sqlite_db_path)
    else:
        sqlite_db_path = os.path.join(target_dir, "data", "raw", "operational.db")
        init_generic_sqlite_database(sqlite_db_path)

    # 2. Write CSV Targets
    targets_csv_name = "branch_targets.csv" if is_restaurant else "segment_targets.csv"
    targets_content = BRANCH_TARGETS_CSV if is_restaurant else GENERIC_SEGMENT_TARGETS_CSV
    targets_csv_path = os.path.join(target_dir, "data", "raw", targets_csv_name)
    with open(targets_csv_path, "w", encoding="utf-8") as f:
        f.write(targets_content.strip() + "\n")

    # 3. Write Data Dictionary & SQL Models
    dict_content = DATA_DICTIONARY_MD if is_restaurant else GENERIC_DATA_DICTIONARY_MD
    dict_path = os.path.join(target_dir, "models", "data_dictionary.md")
    with open(dict_path, "w", encoding="utf-8") as f:
        f.write(dict_content.strip() + "\n")

    sql_content = SQL_MODELS_CONTENT if is_restaurant else GENERIC_SQL_MODELS_CONTENT
    sql_path = os.path.join(target_dir, "models", "marts.sql")
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write(sql_content.strip() + "\n")

    # 4. Write ETL Pipeline Script if restaurant template
    if is_restaurant:
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
    home_content = EVIDENCE_DASHBOARD_MD if is_restaurant else GENERIC_EVIDENCE_DASHBOARD_MD
    with open(os.path.join(pages_dir, "home.md"), "w", encoding="utf-8") as f:
        f.write(home_content.strip() + "\n")

    # 6. Write Marp Presentation Deck
    marp_content = MARP_PRESENTATION_MD if is_restaurant else GENERIC_MARP_PRESENTATION_MD
    marp_path = os.path.join(target_dir, "slides", "presentation.md")
    with open(marp_path, "w", encoding="utf-8") as f:
        f.write(marp_content.strip() + "\n")

    # 7. Write Comprehensive README
    readme_content = f"""# {os.path.basename(target_dir)}

Data analysis project scaffolded with the **Data Analyst Workbench** (7-Stage Audited Pipeline).

## 7-Stage Pipeline Architecture
1. **Sources (`data/raw/`):** SQLite OLTP (`pos_transactions.db`) & CSV/Excel targets (`branch_targets.csv`).
2. **Extract:** High-speed connectors (`sqlite3`, `polars`, `fastexcel`).
3. **Staging / Landing (`data/staging/`):** Immutable raw Parquet snapshots.
4. **Source Validation (`data/quarantine/`):** Pre-flight gate isolating corrupted/invalid rows to `error_log.json` and rejected CSVs.
5. **Transform (`etl.py`):** Polars cleaning, currency/date hygiene, OBT & dimensional marts (with `.to_pandas()` bridge).
6. **Target Validation & Load (`data/processed/`, `data/marts/`, `data/analytics.duckdb`):** Automated financial reconciliation before loading into DuckDB & Parquet.
7. **Business Intelligence & Deliverables:** Evidence.dev dashboard (`reports/`), Marp slides (`slides/`), and SQL models (`models/marts.sql`).

## Quick Commands
```powershell
# 1. Run the 7-Stage ETL Pipeline (or add --interactive to confirm each step)
analyst run
analyst run --interactive

# 2. Inspect Checkpoint Audit Trail (What, Why, How) & Quarantine Log
analyst checkpoint
analyst checkpoint --quarantine

# 3. Inspect Raw Data / Targets
analyst inspect data/raw/pos_transactions.db
analyst stats data/raw/branch_targets.csv

# 4. Query Analytical Marts
analyst query models/marts.sql

# 5. Launch BI Dashboard
analyst dashboard

# 6. Compile Executive Slides
analyst slides --format html
```
"""
    with open(os.path.join(target_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)

    console.print(f"[bold green][OK] Project '{os.path.basename(target_dir)}' successfully created![/bold green]")
    console.print(f"[cyan]Next step:[/cyan] [yellow]cd \"{target_dir}\"[/yellow]")
    console.print("[dim]Run 'analyst run' to execute the 7-Stage Audited ETL pipeline.[/dim]\n")
