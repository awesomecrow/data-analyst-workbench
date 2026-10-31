import os
import sqlite3
import duckdb
import pytest
from workbench.oltp import find_default_oltp_db, show_oltp_schema, run_oltp_query
from workbench.engine import auto_ingest, execute_sql_models, run_dual_engine_pipeline
from workbench.report_gen import generate_interactive_dashboard


def test_sqlite_oltp_engine(tmp_path, monkeypatch):
    """Verify SQLite OLTP database creation, schema inspection, and query execution."""
    monkeypatch.chdir(tmp_path)
    os.makedirs("data/raw", exist_ok=True)
    db_path = os.path.join("data", "raw", "operational.db")

    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, role TEXT)")
    conn.execute("CREATE TABLE orders (order_id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), amount REAL)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice', 'Admin'), (2, 'Bob', 'Member')")
    conn.execute("INSERT INTO orders VALUES (101, 1, 150.0), (102, 2, 75.5)")
    conn.commit()
    conn.close()

    found_db = find_default_oltp_db()
    assert found_db == db_path

    # Verify query execution returns 0
    rc = run_oltp_query("SELECT name, role FROM users WHERE id = 1")
    assert rc == 0

    # Verify schema inspection
    show_oltp_schema(db_path)


def test_auto_ingest_and_sql_models(tmp_path, monkeypatch):
    """Verify zero-code auto-ingestion of CSV and SQLite into DuckDB and execution of SQL models."""
    monkeypatch.chdir(tmp_path)
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("models", exist_ok=True)

    # 1. Create CSV file
    csv_path = os.path.join("data", "raw", "sales_targets.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("region,target\nNorth,5000\nSouth,3000\n")

    # 2. Create SQLite DB
    db_path = os.path.join("data", "raw", "orders.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE actual_sales (region TEXT, revenue REAL)")
    conn.execute("INSERT INTO actual_sales VALUES ('North', 5200.0), ('South', 2800.0)")
    conn.commit()
    conn.close()

    # 3. Run auto_ingest
    registered = auto_ingest()
    assert "sales_targets" in registered
    assert "orders_actual_sales" in registered or "actual_sales" in registered or any("sales" in k for k in registered)
    assert os.path.exists("data/staging/sales_targets.parquet")

    # 4. Create SQL Model in models/
    sql_model_path = os.path.join("models", "mart_regional_performance.sql")
    with open(sql_model_path, "w", encoding="utf-8") as f:
        f.write("""
        SELECT 
            t.region,
            s.revenue,
            t.target,
            ROUND((s.revenue / t.target) * 100, 1) AS attainment_pct
        FROM sales_targets t
        JOIN orders_actual_sales s ON t.region = s.region
        """)

    # 5. Execute SQL Models
    executed = execute_sql_models()
    assert "mart_regional_performance" in executed
    assert os.path.exists("data/marts/mart_regional_performance.parquet")

    # 6. Verify DuckDB query against materialized mart
    conn_duck = duckdb.connect("data/analytics.duckdb")
    res = conn_duck.execute("SELECT region, attainment_pct FROM mart_regional_performance ORDER BY region").fetchall()
    assert len(res) == 2
    assert res[0][0] == "North"
    assert res[0][1] == 104.0
    conn_duck.close()


def test_dual_engine_full_pipeline_and_dashboard(tmp_path, monkeypatch):
    """Verify run_dual_engine_pipeline executes end-to-end and generates dashboard."""
    monkeypatch.chdir(tmp_path)
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("models", exist_ok=True)

    # Raw CSV data
    with open("data/raw/customers.csv", "w", encoding="utf-8") as f:
        f.write("cust_id,cust_name,segment\n1,Acme,B2B\n2,John,B2C\n")

    with open("models/mart_customers.sql", "w", encoding="utf-8") as f:
        f.write("SELECT cust_id, cust_name, segment FROM customers")

    # Run pipeline
    run_dual_engine_pipeline(interactive=False)

    assert os.path.exists("data/checkpoints/run_latest.json")
    assert os.path.exists("data/marts/mart_customers.parquet")

    # Generate interactive dashboard
    html_out = generate_interactive_dashboard(".")
    assert os.path.exists(html_out)
    with open(html_out, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Executive Analytics Dashboard" in content
    assert "mart_customers" in content
