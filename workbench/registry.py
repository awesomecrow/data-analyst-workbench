import os
import time
import duckdb
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from workbench.config import load_config

console = Console()

def list_projects():
    cfg = load_config()
    p_dir = cfg.get("projects_dir")
    
    console.print(Panel.fit(f"[bold cyan]Tracked Projects in:[/bold cyan] [yellow]{p_dir}[/yellow]", border_style="cyan"))

    if not os.path.exists(p_dir):
        console.print("[yellow]Projects directory does not exist yet. Create a project with 'analyst new <name>'[/yellow]\n")
        return

    subdirs = [os.path.join(p_dir, d) for d in os.listdir(p_dir) if os.path.isdir(os.path.join(p_dir, d))]

    if not subdirs:
        console.print(f"[yellow]No projects found in {p_dir}. Run 'analyst new <project-name>' to create one.[/yellow]\n")
        return

    table = Table(title="Data Analyst Project Portfolio", show_header=True, header_style="bold magenta")
    table.add_column("Project Name", style="bold green")
    table.add_column("DuckDB Database")
    table.add_column("BI Dashboard (Evidence)")
    table.add_column("Slides (Marp)")
    table.add_column("Last Modified")

    for sdir in sorted(subdirs):
        pname = os.path.basename(sdir)
        db_file = os.path.join(sdir, "data", "analytics.duckdb")
        db_status = "[dim]None[/dim]"
        if os.path.exists(db_file):
            try:
                conn = duckdb.connect(db_file, read_only=True)
                tables = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()
                t_count = len(tables)
                conn.close()
                db_status = f"[green]Active ({t_count} tables)[/green]"
            except Exception:
                db_status = "[green]Active[/green]"

        dash_status = "[green]Ready[/green]" if os.path.exists(os.path.join(sdir, "reports")) else "[dim]No[/dim]"
        slides_status = "[green]Ready[/green]" if os.path.exists(os.path.join(sdir, "slides", "presentation.md")) else "[dim]No[/dim]"
        
        mtime = os.path.getmtime(sdir)
        mtime_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))

        table.add_row(pname, db_status, dash_status, slides_status, mtime_str)

    console.print(table)
    console.print("[dim]Navigate into any project: 'cd <path>' and run 'analyst dashboard' or 'analyst query'[/dim]\n")
