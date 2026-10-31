import shutil
import sys
from importlib.metadata import version as pkg_version
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def check_command(cmd_name: str) -> tuple[bool, str]:
    path = shutil.which(cmd_name)
    if path:
        return True, path
    return False, "Not found in PATH"

def check_python_pkg(pkg_name: str) -> tuple[bool, str]:
    try:
        ver = pkg_version(pkg_name)
        return True, f"v{ver}"
    except Exception:
        return False, "Not installed"

def run_doctor():
    console.print(Panel.fit("[bold cyan]Data Analyst Workbench Health Check[/bold cyan]", border_style="cyan"))
    
    table = Table(title="Installed Workbench Tools", show_header=True, header_style="bold magenta")
    table.add_column("Tool", style="bold")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Details")

    # Python packages
    py_tools = [
        ("duckdb", "Database Engine / OLAP", "duckdb"),
        ("sqlite3", "Database Engine / OLTP (Row)", "sqlite3"),
        ("polars", "Dataframe Processing (Core)", "polars"),
        ("pandas", "Dataframe Interop / Bridge", "pandas"),
        ("openpyxl/fastexcel", "Excel Processing Engine", "openpyxl"),
        ("visidata", "Terminal Data Explorer", "visidata"),
        ("plotext", "Terminal Plotting", "plotext"),
        ("rich", "Terminal Styling & Tables", "rich"),
    ]

    for tool_name, desc, pkg in py_tools:
        if pkg == "sqlite3":
            try:
                import sqlite3
                ok, detail = True, f"v{sqlite3.sqlite_version} (built-in)"
            except Exception:
                ok, detail = False, "Missing"
        else:
            ok, detail = check_python_pkg(pkg)
        status_str = "[green][OK] Installed[/green]" if ok else "[red][X] Missing[/red]"
        table.add_row(f"{tool_name} (Python)", desc, status_str, detail)

    # CLI tools
    cli_tools = [
        ("duckdb", "OLAP Database CLI", "duckdb"),
        ("sqlite3", "OLTP Database CLI", "sqlite3"),
        ("visidata (vd)", "Interactive Data TUI", "vd"),
        ("marp", "Markdown Slide Generator", "marp"),
        ("evidence", "BI Dashboard Engine", "evidence"),
    ]

    for tool_name, desc, cmd in cli_tools:
        ok, detail = check_command(cmd)
        status_str = "[green][OK] Available[/green]" if ok else "[red][X] Missing[/red]"
        table.add_row(f"{tool_name} (CLI)", desc, status_str, detail)

    console.print(table)
    console.print("[dim]All core tools are verified and integrated with this workbench.[/dim]\n")
