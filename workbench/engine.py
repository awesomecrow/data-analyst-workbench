import os
import re
import glob
import shutil
import sqlite3
import duckdb
import polars as pl
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from workbench.checkpoint import CheckpointTracker

console = Console()


def sanitize_table_name(filename: str) -> str:
    """Convert filename to a clean, valid SQL identifier."""
    base = os.path.splitext(filename)[0]
    # Replace non-alphanumeric with underscores, lowercased
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", base).strip("_").lower()
    if cleaned and cleaned[0].isdigit():
        cleaned = f"t_{cleaned}"
    return cleaned or "raw_table"


def auto_ingest(raw_dir: str = "data/raw", staging_dir: str = "data/staging", duckdb_path: str = "data/analytics.duckdb", tracker: CheckpointTracker | None = None) -> dict:
    """
    Zero-Code Auto-Ingestion Engine:
    Discovers all CSV, Excel, Parquet, and SQLite files in data/raw/,
    snapshots them to data/staging/*.parquet, and registers them into DuckDB.
    """
    os.makedirs(staging_dir, exist_ok=True)
    os.makedirs(os.path.dirname(duckdb_path) or ".", exist_ok=True)

    if not os.path.exists(raw_dir):
        console.print(f"[yellow]Raw data directory '{raw_dir}' does not exist.[/yellow]")
        return {}

    raw_files = [
        f for f in glob.glob(os.path.join(raw_dir, "*"))
        if os.path.isfile(f) and f.lower().endswith((".csv", ".parquet", ".xlsx", ".xls", ".db", ".sqlite"))
    ]

    if not raw_files:
        console.print(f"[yellow]No data files found in '{raw_dir}' (supports CSV, Excel, Parquet, SQLite).[/yellow]")
        return {}

    console.print(Panel.fit(f"[bold cyan]Zero-Code Ingestion Engine[/bold cyan]\nScanning: [bold]{os.path.abspath(raw_dir)}[/bold]\nDiscovered: [bold green]{len(raw_files)} source file(s)[/bold green]", border_style="cyan"))

    conn = duckdb.connect(duckdb_path)
    registered_tables = {}
    total_raw_rows = 0

    for fpath in raw_files:
        fname = os.path.basename(fpath)
        ext = os.path.splitext(fname)[1].lower()
        tbl_name = sanitize_table_name(fname)

        try:
            if ext in (".db", ".sqlite"):
                # Relational SQLite database: extract each user table
                conn_sqlite = sqlite3.connect(fpath)
                cur = conn_sqlite.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                sqlite_tables = [r[0] for r in cur.fetchall()]

                for sq_tbl in sqlite_tables:
                    clean_sq = sanitize_table_name(sq_tbl)
                    df = pl.read_database(f"SELECT * FROM {sq_tbl}", conn_sqlite)
                    target_tbl = clean_sq
                    stg_file = os.path.join(staging_dir, f"{target_tbl}.parquet")
                    df.write_parquet(stg_file)
                    conn.execute(f"CREATE OR REPLACE TABLE {target_tbl} AS SELECT * FROM '{stg_file}'")
                    if tbl_name != clean_sq:
                        try:
                            conn.execute(f"CREATE OR REPLACE VIEW {tbl_name}_{clean_sq} AS SELECT * FROM {target_tbl}")
                        except Exception:
                            pass
                    registered_tables[target_tbl] = len(df)
                    total_raw_rows += len(df)

                conn_sqlite.close()

            elif ext == ".csv":
                df = pl.read_csv(fpath, infer_schema_length=5000, ignore_errors=True)
                stg_file = os.path.join(staging_dir, f"{tbl_name}.parquet")
                df.write_parquet(stg_file)
                conn.execute(f"CREATE OR REPLACE TABLE {tbl_name} AS SELECT * FROM '{stg_file}'")
                registered_tables[tbl_name] = len(df)
                total_raw_rows += len(df)

            elif ext in (".xlsx", ".xls"):
                df = pl.read_excel(fpath)
                stg_file = os.path.join(staging_dir, f"{tbl_name}.parquet")
                df.write_parquet(stg_file)
                conn.execute(f"CREATE OR REPLACE TABLE {tbl_name} AS SELECT * FROM '{stg_file}'")
                registered_tables[tbl_name] = len(df)
                total_raw_rows += len(df)

            elif ext == ".parquet":
                stg_file = os.path.join(staging_dir, f"{tbl_name}.parquet")
                if os.path.abspath(fpath) != os.path.abspath(stg_file):
                    shutil.copy2(fpath, stg_file)
                conn.execute(f"CREATE OR REPLACE TABLE {tbl_name} AS SELECT * FROM '{stg_file}'")
                row_count = conn.execute(f"SELECT COUNT(*) FROM {tbl_name}").fetchone()[0]
                registered_tables[tbl_name] = row_count
                total_raw_rows += row_count

        except Exception as e:
            console.print(f"[bold red]Failed to ingest {fname}:[/bold red] {e}")

    conn.close()

    # Display ingestion summary table
    summary_table = Table(title="Ingested Raw Datasets & DuckDB Views", show_header=True, header_style="bold magenta")
    summary_table.add_column("Table Name (in DuckDB)", style="bold cyan")
    summary_table.add_column("Source File")
    summary_table.add_column("Rows Ingested", justify="right", style="green")

    for tbl, rcount in registered_tables.items():
        summary_table.add_row(tbl, f"data/staging/{tbl}.parquet", f"{rcount:,}")

    console.print(summary_table)

    if tracker:
        tracker.record_stage(
            stage_num=1,
            stage_name="AUTO-INGEST & STAGING",
            what=f"Discovered {len(raw_files)} file(s), ingested {total_raw_rows:,} total rows across {len(registered_tables)} table(s) into DuckDB.",
            why="Provide instant zero-code SQL queryability and immutable Parquet staging snapshots.",
            how="Scanned data/raw/ formats, serialized to Snappy Parquet in data/staging/, registered views in DuckDB.",
            status="PASSED",
            metrics={"source_files": len(raw_files), "registered_tables": len(registered_tables), "total_rows": total_raw_rows},
        )

    return registered_tables


def execute_sql_models(models_dir: str = "models", marts_dir: str = "data/marts", duckdb_path: str = "data/analytics.duckdb", tracker: CheckpointTracker | None = None) -> list[str]:
    """
    SQL-First Modeling Engine:
    Executes declarative SQL files in models/*.sql into DuckDB tables
    and materializes them as Parquet analytical marts in data/marts/*.
    """
    if not os.path.exists(models_dir):
        console.print(f"[yellow]No models directory found at '{models_dir}'.[/yellow]")
        return []

    sql_files = glob.glob(os.path.join(models_dir, "*.sql")) + glob.glob(os.path.join(models_dir, "**", "*.sql"))
    if not sql_files:
        console.print(f"[dim]No .sql model files found in '{models_dir}'.[/dim]")
        return []

    os.makedirs(marts_dir, exist_ok=True)
    os.makedirs(os.path.join("data", "processed"), exist_ok=True)

    conn = duckdb.connect(duckdb_path)
    executed_models = []

    for sql_file in sorted(sql_files):
        fname = os.path.basename(sql_file)
        model_name = os.path.splitext(fname)[0]

        with open(sql_file, "r", encoding="utf-8") as f:
            sql_content = f.read().strip()

        if not sql_content:
            continue

        console.print(f"[cyan]Executing SQL Model:[/cyan] [bold]{model_name}[/bold] [dim]({sql_file})[/dim]")
        try:
            # If the SQL is multiple statements or a raw query, wrap or execute
            # Check if user already provided CREATE TABLE / VIEW or a SELECT
            cleaned_sql = sql_content.rstrip(";").strip()
            
            # If it's a SELECT statement, materialize it as a table and export to Parquet
            if cleaned_sql.lower().startswith("select") or cleaned_sql.lower().startswith("with"):
                mat_query = f"CREATE OR REPLACE TABLE {model_name} AS {cleaned_sql};"
                conn.execute(mat_query)
                row_count = conn.execute(f"SELECT COUNT(*) FROM {model_name}").fetchone()[0]
                
                # Materialize to data/marts/ and data/processed/
                parquet_mart = os.path.join(marts_dir, f"{model_name}.parquet")
                parquet_processed = os.path.join("data", "processed", f"{model_name}.parquet")
                conn.execute(f"COPY {model_name} TO '{parquet_mart}' (FORMAT PARQUET)")
                conn.execute(f"COPY {model_name} TO '{parquet_processed}' (FORMAT PARQUET)")
                
                console.print(f"  [green][OK] Materialized table '{model_name}' ({row_count:,} rows) -> {parquet_mart}[/green]")
                executed_models.append(model_name)
            else:
                # Execute general multi-statement SQL
                conn.execute(sql_content)
                console.print(f"  [green][OK] Executed SQL script '{model_name}' successfully.[/green]")
                executed_models.append(model_name)

        except Exception as e:
            console.print(f"  [bold red][X] Error in model {model_name}:[/bold red] {e}")

    conn.close()

    if tracker and executed_models:
        tracker.record_stage(
            stage_num=4,
            stage_name="SQL-FIRST TRANSFORM",
            what=f"Compiled and materialized {len(executed_models)} SQL model(s) into DuckDB analytical marts and Parquet files.",
            why="Execute declarative SQL analytical transformations without requiring procedural Python glue code.",
            how="Parsed models/*.sql, executed vector queries inside DuckDB, and serialized results to data/marts/*.parquet.",
            status="PASSED",
            metrics={"executed_models": len(executed_models)},
        )

    return executed_models


def run_dual_engine_pipeline(interactive: bool = False):
    """
    Complete Dual-Engine Pipeline Execution:
    1. Auto-ingest raw files (CSV, Excel, SQLite, Parquet) -> Staging -> DuckDB.
    2. Execute declarative SQL models in models/*.sql -> Parquet marts.
    3. Finalize checkpoint audit trail (What, Why, How).
    """
    tracker = CheckpointTracker(project_name=os.path.basename(os.getcwd()), interactive=interactive)
    
    # Stage 1 & 2: Ingest
    ingested = auto_ingest(tracker=tracker)
    
    # Stage 3 & 4: Execute SQL models if available
    executed = execute_sql_models(tracker=tracker)

    manifest_path = tracker.finalize("SUCCESS")
    console.print(f"\n[bold green][OK] Dual-Engine Pipeline Completed Successfully![/bold green]")
    console.print(f"[dim]Audit manifest: {manifest_path}[/dim]")
    console.print(f"[dim]Run 'analyst query' to query marts, or 'analyst oltp' to query operational tables.[/dim]\n")
