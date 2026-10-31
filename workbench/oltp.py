import os
import sys
import glob
import sqlite3
import subprocess
import shutil
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def find_default_oltp_db(custom_path: str | None = None) -> str | None:
    """Locate the active SQLite OLTP database in the current project."""
    if custom_path and os.path.exists(custom_path):
        return custom_path

    # Check common locations
    candidates = [
        os.path.join("data", "raw", "operational.db"),
        os.path.join("data", "raw", "pos_transactions.db"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    # Search any .db or .sqlite file in data/raw/
    db_files = glob.glob(os.path.join("data", "raw", "*.db")) + glob.glob(os.path.join("data", "raw", "*.sqlite"))
    if db_files:
        return db_files[0]

    return None


def show_oltp_schema(db_path: str):
    """Display normalized 3NF schema, tables, columns, and foreign keys from OLTP database."""
    if not os.path.exists(db_path):
        console.print(f"[bold red]OLTP database not found:[/bold red] {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    tables = [r[0] for r in cur.fetchall()]

    if not tables:
        console.print(f"[yellow]No user tables found in OLTP database: {db_path}[/yellow]")
        conn.close()
        return

    console.print(
        Panel.fit(
            f"[bold cyan]SQLite OLTP Relational Schema Inspection (3NF)[/bold cyan]\n"
            f"Database File: [bold]{os.path.abspath(db_path)}[/bold]\n"
            f"Total Relational Tables: [bold green]{len(tables)}[/bold green]",
            border_style="cyan",
        )
    )

    for tbl in tables:
        cur.execute(f"PRAGMA table_info({tbl});")
        columns = cur.fetchall()

        cur.execute(f"PRAGMA foreign_key_list({tbl});")
        fks = cur.fetchall()
        fk_map = {fk[3]: f"-> {fk[2]}.{fk[4]}" for fk in fks}

        cur.execute(f"SELECT COUNT(*) FROM {tbl};")
        row_count = cur.fetchone()[0]

        table_view = Table(
            title=f"Table: [bold green]{tbl}[/bold green] ({row_count:,} rows)",
            show_header=True,
            header_style="bold magenta",
        )
        table_view.add_column("CID", justify="right", style="dim", width=4)
        table_view.add_column("Column Name", style="bold")
        table_view.add_column("Data Type")
        table_view.add_column("Not Null?")
        table_view.add_column("Primary Key?")
        table_view.add_column("Foreign Key Reference", style="yellow")

        for col in columns:
            cid, name, dtype, notnull, dflt, pk = col
            is_pk = "[bold green]YES (PK)[/bold green]" if pk > 0 else "No"
            is_nn = "Yes" if notnull else "No"
            fk_ref = fk_map.get(name, "-")
            table_view.add_row(str(cid), name, dtype or "BLOB/TEXT", is_nn, is_pk, fk_ref)

        console.print(table_view)

    conn.close()


def run_oltp_query(query: str | None, custom_db: str | None = None, show_schema: bool = False):
    """Execute query against SQLite OLTP engine or launch interactive shell."""
    db_path = find_default_oltp_db(custom_db)

    if not db_path:
        console.print("[bold red]No SQLite OLTP database found in 'data/raw/'.[/bold red]")
        console.print("[dim]Place a .db / .sqlite file in data/raw/ or specify via --db <path>[/dim]")
        return

    if show_schema:
        show_oltp_schema(db_path)
        return

    if not query:
        # Launch interactive SQLite shell if available, or python-based prompt
        sqlite3_cli = shutil.which("sqlite3")
        if sqlite3_cli:
            console.print(f"[bold cyan]Launching SQLite CLI shell for {db_path}...[/bold cyan]")
            subprocess.run([sqlite3_cli, db_path])
        else:
            console.print(f"[bold cyan]Interactive Python SQLite shell for {db_path} (Type 'exit' or Ctrl+C to quit)[/bold cyan]")
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            try:
                while True:
                    cmd = input("sqlite (oltp)> ").strip()
                    if not cmd:
                        continue
                    if cmd.lower() in ("exit", "quit"):
                        break
                    if cmd == ".tables":
                        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
                        print("  ".join(r[0] for r in cur.fetchall()))
                        continue
                    if cmd == ".schema":
                        show_oltp_schema(db_path)
                        continue

                    try:
                        cur.execute(cmd)
                        rows = cur.fetchall()
                        if cur.description:
                            col_names = [d[0] for d in cur.description]
                            tbl = Table(show_header=True, header_style="bold magenta")
                            for c in col_names:
                                tbl.add_column(c)
                            for row in rows[:50]:
                                tbl.add_row(*[str(v) if v is not None else "[dim]NULL[/dim]" for v in row])
                            console.print(tbl)
                            console.print(f"[dim]({len(rows)} row(s) returned)[/dim]")
                    except Exception as e:
                        console.print(f"[bold red]Query error:[/bold red] {e}")
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Exited SQLite shell.[/yellow]")
            finally:
                conn.close()
        return

    # Execute single query string or .sql file
    if os.path.exists(query) and query.endswith(".sql"):
        with open(query, "r", encoding="utf-8") as f:
            sql_text = f.read()
    else:
        sql_text = query

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(sql_text)
        rows = cur.fetchall()

        if cur.description:
            col_names = [d[0] for d in cur.description]
            tbl = Table(
                title=f"OLTP Query Results ({len(rows)} rows from {os.path.basename(db_path)})",
                show_header=True,
                header_style="bold magenta",
            )
            for c in col_names:
                tbl.add_column(c)
            for row in rows[:100]:
                tbl.add_row(*[str(v) if v is not None else "[dim]NULL[/dim]" for v in row])
            console.print(tbl)
            if len(rows) > 100:
                console.print(f"[dim]Showing first 100 of {len(rows)} total rows.[/dim]")
        else:
            conn.commit()
            console.print(f"[bold green]Query executed successfully ({cur.rowcount} row(s) affected).[/bold green]")
        conn.close()
        return 0
    except Exception as e:
        console.print(f"[bold red]OLTP Query Error:[/bold red] {e}")
        return 1
