import os
import polars as pl
import plotext as plt
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def show_stats(file_path: str):
    if not os.path.exists(file_path):
        console.print(f"[bold red]Error:[/bold red] File not found: {file_path}")
        return

    console.print(f"\n[bold cyan]Auditing dataset:[/bold cyan] [yellow]{file_path}[/yellow]")
    
    # Load with polars
    try:
        if file_path.endswith(".parquet"):
            df = pl.read_parquet(file_path)
        elif file_path.endswith(".csv"):
            df = pl.read_csv(file_path)
        elif file_path.endswith(".json") or file_path.endswith(".ndjson"):
            df = pl.read_ndjson(file_path) if file_path.endswith(".ndjson") else pl.read_json(file_path)
        else:
            # Fallback to csv
            df = pl.read_csv(file_path)
    except Exception as e:
        console.print(f"[bold red]Failed to read file with Polars:[/bold red] {e}")
        return

    num_rows, num_cols = df.shape
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    
    console.print(Panel(
        f"Rows: [bold green]{num_rows:,}[/bold green] | "
        f"Columns: [bold green]{num_cols}[/bold green] | "
        f"File Size: [bold green]{size_mb:.2f} MB[/bold green]",
        title="Dataset Overview",
        border_style="green"
    ))

    # Schema & Nulls table
    schema_table = Table(title="Column Schema & Null Diagnostics", show_header=True, header_style="bold magenta")
    schema_table.add_column("Column")
    schema_table.add_column("Polars Dtype")
    schema_table.add_column("Null Count")
    schema_table.add_column("Null %")
    schema_table.add_column("Sample Value")

    for col in df.columns:
        null_cnt = df[col].null_count()
        null_pct = (null_cnt / num_rows) * 100 if num_rows > 0 else 0
        sample_val = str(df[col].drop_nulls().head(1).to_list()[0]) if (num_rows - null_cnt) > 0 else "N/A"
        if len(sample_val) > 40:
            sample_val = sample_val[:37] + "..."
        
        null_style = "[red]" if null_pct > 10 else "[green]"
        schema_table.add_row(
            col,
            str(df[col].dtype),
            f"{null_style}{null_cnt:,}[/]",
            f"{null_style}{null_pct:.1f}%[/]",
            sample_val
        )

    console.print(schema_table)

    # Plot terminal chart for first non-id numeric column
    numeric_cols = [c for c in df.columns if df[c].dtype.is_numeric() and "id" not in c.lower()]
    if not numeric_cols:
        numeric_cols = [c for c in df.columns if df[c].dtype.is_numeric()]
        
    if numeric_cols:
        target_col = numeric_cols[0]
        vals = [float(v) for v in df[target_col].drop_nulls().to_list()]
        if vals:
            console.print(f"\n[bold yellow]Terminal Histogram for metric '{target_col}':[/bold yellow]")
            try:
                # Support plotext v6 figure API
                fig = getattr(plt, "figure", plt)
                if hasattr(fig, "clear"):
                    fig.clear()
                if hasattr(fig, "hist"):
                    fig.hist(vals, bins=8)
                if hasattr(fig, "title"):
                    fig.title(f"Distribution of {target_col}")
                if hasattr(fig, "show"):
                    fig.show()
            except Exception as e:
                console.print(f"[dim](Plotext preview skipped: {e})[/dim]")
            console.print()
