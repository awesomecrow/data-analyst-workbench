import os
import sys
import argparse
import subprocess
import shutil
from rich.console import Console

from workbench.doctor import run_doctor
from workbench.templates import scaffold_project
from workbench.inspect_tool import inspect_data
from workbench.stats import show_stats
from workbench.query_tool import run_query
from workbench.config import print_config, set_config_value, load_config
from workbench.registry import list_projects
from workbench.ai import ask_ai
from workbench.checkpoint import show_checkpoint
from workbench.oltp import run_oltp_query
from workbench.engine import auto_ingest, execute_sql_models, run_dual_engine_pipeline

console = Console()

def run_etl(interactive: bool = False):
    if os.path.exists("etl.py"):
        console.print("[cyan]Executing custom 7-Stage ETL pipeline (etl.py)...[/cyan]")
        cmd = [sys.executable, "etl.py"]
        if interactive:
            cmd.append("--interactive")
        subprocess.run(cmd)
    else:
        console.print("[cyan]No custom etl.py found. Running declarative Dual-Engine pipeline...[/cyan]")
        run_dual_engine_pipeline(interactive=interactive)

def launch_dashboard(port: int = 3000, force_evidence: bool = False):
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)

    if force_evidence:
        evidence_cli = shutil.which("evidence") or shutil.which("evd")
        if not evidence_cli:
            console.print("[bold red]Evidence CLI not found in PATH.[/bold red]")
            return
        console.print(f"[bold green]Starting Evidence BI Dashboard on port {port}...[/bold green]")
        try:
            subprocess.run([evidence_cli, "dev", "--port", str(port)], cwd=reports_dir, shell=True)
        except KeyboardInterrupt:
            console.print("\n[yellow]Dashboard server stopped.[/yellow]")
        return

    # Generate or refresh interactive standalone dashboard
    from workbench.report_gen import generate_interactive_dashboard
    console.print(f"[cyan]Compiling data-driven interactive BI dashboard...[/cyan]")
    dash_path = generate_interactive_dashboard()
    console.print(f"[bold green][OK] Dashboard compiled to {dash_path}[/bold green]")
    console.print(f"[bold green]Serving interactive dashboard at http://localhost:{port}...[/bold green]")
    console.print(f"[dim](Pass --evidence to launch Evidence Studio dev server instead)[/dim]")

    import http.server
    import socketserver
    import webbrowser

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=reports_dir, **kwargs)

    try:
        webbrowser.open(f"http://localhost:{port}/index.html")
    except Exception:
        pass

    try:
        with socketserver.TCPServer(("", port), Handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard server stopped.[/yellow]")

def compile_slides(fmt: str = "html"):
    slides_md = os.path.join("slides", "presentation.md")
    if not os.path.exists(slides_md):
        console.print(f"[bold red]Slide deck not found at {slides_md}[/bold red]")
        return

    marp_cmd = shutil.which("marp")
    if not marp_cmd:
        console.print("[bold red]Marp CLI not found in PATH.[/bold red]")
        return

    out_file = os.path.join("slides", f"presentation.{fmt}")
    cmd = [marp_cmd, "--no-stdin", slides_md, "-o", out_file]
    if fmt == "html":
        cmd.append("--html")
    elif fmt == "pdf":
        cmd.append("--pdf")

    console.print(f"[cyan]Compiling slides to {out_file}...[/cyan]")
    try:
        res = subprocess.run(cmd, shell=True)
        if res.returncode == 0:
            console.print(f"[bold green][OK] Presentation compiled successfully: {out_file}[/bold green]")
        else:
            console.print(f"[bold red]Marp compilation failed with code {res.returncode}[/bold red]")
    except Exception as e:
        console.print(f"[bold red]Failed to run Marp:[/bold red] {e}")

def main():
    parser = argparse.ArgumentParser(
        prog="analyst",
        description="Data Analyst Workbench CLI -- Open-Source, Fast & Context-Aware"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # doctor
    subparsers.add_parser("doctor", help="Check installation of all workbench tools")

    # list
    subparsers.add_parser("list", help="List and track all analytics projects in your portfolio")

    # config
    config_parser = subparsers.add_parser("config", help="View or modify workbench configuration (default directories, AI keys)")
    config_parser.add_argument("--set-dir", dest="set_dir", help="Set the default projects parent directory")
    config_parser.add_argument("--set-key", dest="set_key", help="Set the AI API key (Gemini / OpenAI)")
    config_parser.add_argument("--set-provider", dest="set_provider", choices=["gemini", "openai", "ollama"], help="Set the AI provider")

    # new
    new_parser = subparsers.add_parser("new", help="Create a new context-specific analytics project")
    new_parser.add_argument("name", help="Name of the new project directory (or relative/absolute path)")
    new_parser.add_argument("--path", "-p", default=None, help="Target destination directory where the project folder will be created")
    new_parser.add_argument("--template", "-t", default="generic", help="Project template (default: generic, or 'restaurant-sales')")

    # ask (AI)
    ask_parser = subparsers.add_parser("ask", help="Ask AI a natural language question about your dataset/database")
    ask_parser.add_argument("question", help="Question in plain English (e.g. 'Which segments had the lowest performance?')")
    ask_parser.add_argument("--db", default="data/analytics.duckdb", help="Path to DuckDB database")

    # inspect
    inspect_parser = subparsers.add_parser("inspect", help="Open dataset in VisiData for interactive exploration")
    inspect_parser.add_argument("file", nargs="?", default=None, help="File path to inspect")

    # stats
    stats_parser = subparsers.add_parser("stats", help="Display schema, null profile, and terminal charts with Polars & Plotext")
    stats_parser.add_argument("file", help="File path to profile (CSV, Parquet, JSON)")

    # oltp
    oltp_parser = subparsers.add_parser("oltp", help="Execute query or inspect schema on SQLite OLTP database")
    oltp_parser.add_argument("sql", nargs="?", default=None, help="SQL query string or path to .sql file (opens interactive shell if omitted)")
    oltp_parser.add_argument("--db", default=None, help="Path to SQLite database (defaults to data/raw/*.db)")
    oltp_parser.add_argument("--schema", "-s", action="store_true", help="Inspect normalized 3NF schema, tables, and foreign keys")

    # ingest
    ingest_parser = subparsers.add_parser("ingest", help="Zero-code auto-ingest CSV, Excel, Parquet, and SQLite into Staging & DuckDB")
    ingest_parser.add_argument("--raw", default="data/raw", help="Directory containing raw data files")
    ingest_parser.add_argument("--staging", default="data/staging", help="Target directory for staging Parquet files")
    ingest_parser.add_argument("--db", default="data/analytics.duckdb", help="Path to DuckDB database")

    # query
    query_parser = subparsers.add_parser("query", help="Run DuckDB query or SQL file and display styled Rich table")
    query_parser.add_argument("sql", nargs="?", default=None, help="SQL string or path to .sql file (opens interactive shell if omitted)")
    query_parser.add_argument("--db", default="data/analytics.duckdb", help="Path to DuckDB database")

    # run
    run_parser = subparsers.add_parser("run", help="Execute the project's 7-Stage ETL pipeline (etl.py)")
    run_parser.add_argument("--interactive", "-i", action="store_true", help="Pause at each checkpoint for user confirmation")

    # checkpoint
    cp_parser = subparsers.add_parser("checkpoint", help="Inspect ETL pipeline checkpoints (What, Why, How) and quarantine logs")
    cp_parser.add_argument("--list", "-l", action="store_true", help="List historical checkpoint runs")
    cp_parser.add_argument("--quarantine", "-q", action="store_true", help="Show quarantined / rejected records log")
    cp_parser.add_argument("--run-id", default=None, help="Inspect a specific historical run ID")

    # dashboard
    dash_parser = subparsers.add_parser("dashboard", help="Start the interactive data-driven BI dashboard (or Evidence Studio)")
    dash_parser.add_argument("--port", "-p", type=int, default=3000, help="Port to serve dashboard on")
    dash_parser.add_argument("--evidence", "-e", action="store_true", help="Launch Evidence Studio dev server instead of local offline dashboard")

    # slides
    slides_parser = subparsers.add_parser("slides", help="Compile Marp presentation deck to HTML or PDF")
    slides_parser.add_argument("--format", "-f", choices=["html", "pdf"], default="html", help="Output format (html or pdf)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "doctor":
        run_doctor()
    elif args.command == "list":
        list_projects()
    elif args.command == "config":
        if args.set_dir:
            set_config_value("projects_dir", os.path.abspath(args.set_dir))
        elif args.set_key:
            set_config_value("api_key", args.set_key)
        elif args.set_provider:
            set_config_value("ai_provider", args.set_provider)
        else:
            print_config()
    elif args.command == "new":
        scaffold_project(args.name, args.template, target_path=args.path)
    elif args.command == "ask":
        ask_ai(args.question, args.db)
    elif args.command == "inspect":
        inspect_data(args.file)
    elif args.command == "stats":
        show_stats(args.file)
    elif args.command == "oltp":
        run_oltp_query(args.sql, custom_db=args.db, show_schema=args.schema)
    elif args.command == "ingest":
        auto_ingest(raw_dir=args.raw, staging_dir=args.staging, duckdb_path=args.db)
    elif args.command == "query":
        run_query(args.sql, args.db)
    elif args.command == "run":
        run_etl(interactive=args.interactive)
    elif args.command == "checkpoint":
        show_checkpoint(list_runs=args.list, show_quarantine=args.quarantine, run_id=args.run_id)
    elif args.command == "dashboard":
        launch_dashboard(args.port, force_evidence=args.evidence)
    elif args.command == "slides":
        compile_slides(args.format)

if __name__ == "__main__":
    main()
