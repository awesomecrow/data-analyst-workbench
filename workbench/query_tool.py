import os
import time
import subprocess
import shutil
import duckdb
from rich.console import Console
from rich.table import Table

console = Console()

def run_query(sql_or_file: str | None = None, db_path: str = "data/analytics.duckdb"):
    duckdb_cli = shutil.which("duckdb")
    
    # If no argument given, launch DuckDB interactive shell
    if not sql_or_file:
        if not duckdb_cli:
            console.print("[bold red]DuckDB CLI not found in PATH.[/bold red]")
            return
        db_arg = db_path if os.path.exists(db_path) else ":memory:"
        console.print(f"[bold green]Starting interactive DuckDB shell ({db_arg})...[/bold green]")
        subprocess.run([duckdb_cli, db_arg])
        return

    # Check if sql_or_file is a file path
    if os.path.exists(sql_or_file):
        with open(sql_or_file, "r", encoding="utf-8") as f:
            query = f.read().strip()
        console.print(f"[dim]Executing query from {sql_or_file}...[/dim]")
    else:
        query = sql_or_file.strip()

    # Determine database connection
    try:
        t0 = time.time()
        conn = duckdb.connect(db_path if os.path.exists(db_path) else ":memory:")
        rel = conn.sql(query)
        res = rel.fetchall()
        col_names = rel.columns
        elapsed = (time.time() - t0) * 1000

        # Render rich table
        table = Table(title=f"Query Results ({len(res)} rows in {elapsed:.1f}ms)", show_header=True, header_style="bold cyan")
        for col in col_names:
            table.add_column(str(col))

        # Show up to 50 rows
        for row in res[:50]:
            table.add_row(*[str(val) if val is not None else "[dim]NULL[/dim]" for val in row])

        console.print(table)
        if len(res) > 50:
            console.print(f"[dim](Showing first 50 of {len(res)} rows)[/dim]")

    except Exception as e:
        console.print(f"[bold red]Query Error:[/bold red] {e}")
