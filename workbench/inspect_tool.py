import os
import glob
import subprocess
import shutil
from rich.console import Console

console = Console()

def inspect_data(file_path: str | None = None):
    vd_path = shutil.which("vd")
    if not vd_path:
        console.print("[bold red]VisiData (`vd`) not found in PATH.[/bold red]")
        return

    if not file_path:
        # Search for candidates in current directory
        candidates = glob.glob("data/**/*.csv", recursive=True) + \
                     glob.glob("data/**/*.parquet", recursive=True) + \
                     glob.glob("data/**/*.xlsx", recursive=True) + \
                     glob.glob("data/**/*.db", recursive=True) + \
                     glob.glob("data/**/*.sqlite", recursive=True) + \
                     glob.glob("*.csv") + glob.glob("*.parquet") + glob.glob("*.xlsx") + glob.glob("*.db")
        if candidates:
            file_path = candidates[0]
            console.print(f"[cyan]Auto-detected data file:[/cyan] [yellow]{file_path}[/yellow]")
        else:
            console.print("[yellow]No data file specified and no CSV/Parquet files found in data/.[/yellow]")
            return

    if not os.path.exists(file_path):
        console.print(f"[bold red]File not found:[/bold red] {file_path}")
        return

    console.print(f"[bold green]Opening VisiData on {file_path}... (Press 'q' inside VisiData to exit)[/bold green]")
    try:
        subprocess.run([vd_path, file_path])
    except Exception as e:
        console.print(f"[bold red]Failed to launch VisiData:[/bold red] {e}")
