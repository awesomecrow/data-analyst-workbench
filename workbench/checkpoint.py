import os
import sys
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class CheckpointTracker:
    """
    Structured Checkpoint & Quarantine Audit Engine (What, Why, How).
    Tracks every stage of the ETL pipeline:
    Sources -> Extract -> Staging -> Source Validation -> Transform -> Target Validation -> Load Marts.
    """

    def __init__(self, project_name: str = "analytics-pipeline", interactive: bool = False):
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.project_name = project_name
        self.interactive = interactive
        self.started_at = datetime.now().isoformat(timespec="seconds")
        self.stages = []
        self.quarantine_entries = []
        self.overall_status = "RUNNING"

        os.makedirs(os.path.join("data", "checkpoints"), exist_ok=True)
        os.makedirs(os.path.join("data", "quarantine"), exist_ok=True)
        os.makedirs(os.path.join("data", "staging"), exist_ok=True)

    def record_stage(
        self,
        stage_num: int,
        stage_name: str,
        what: str,
        why: str,
        how: str,
        status: str = "PASSED",
        metrics: dict | None = None,
    ):
        entry = {
            "stage_num": stage_num,
            "stage_name": stage_name,
            "status": status,
            "what": what,
            "why": why,
            "how": how,
            "metrics": metrics or {},
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        self.stages.append(entry)

        status_badge = "[bold green][OK] PASSED[/bold green]"
        if status == "WARNING":
            status_badge = "[bold yellow][!] WARNING[/bold yellow]"
        elif status == "FAILED":
            status_badge = "[bold red][X] FAILED[/bold red]"
            self.overall_status = "FAILED"

        console.print(
            f"\n[bold cyan]Checkpoint {stage_num}: {stage_name}[/bold cyan] {status_badge}"
        )
        console.print(f"  [bold white]WHAT :[/bold white] {what}")
        console.print(f"  [bold yellow]WHY  :[/bold yellow] {why}")
        console.print(f"  [bold green]HOW  :[/bold green] {how}")
        if metrics:
            metrics_str = ", ".join(f"{k}={v}" for k, v in metrics.items())
            console.print(f"  [dim]METRICS: {metrics_str}[/dim]")

        if self.interactive and sys.stdin.isatty():
            ans = input("  --> Proceed to next stage? [Y/n]: ").strip().lower()
            if ans in ("n", "no"):
                self.overall_status = "ABORTED_BY_USER"
                self.finalize()
                console.print("[bold yellow]Pipeline execution stopped by user at checkpoint.[/bold yellow]")
                sys.exit(0)

    def log_quarantine(
        self,
        gate: str,
        source_table: str,
        reason: str,
        rejected_count: int,
        sample_records: list[dict] | None = None,
        csv_path: str | None = None,
    ):
        q_entry = {
            "run_id": self.run_id,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "gate": gate,
            "source_table": source_table,
            "reason": reason,
            "rejected_count": rejected_count,
            "csv_artifact": csv_path or "",
            "sample_records": sample_records or [],
        }
        self.quarantine_entries.append(q_entry)
        console.print(
            f"  [bold red][QUARANTINE / ERROR LOG][/bold red] {rejected_count} row(s) from '{source_table}' "
            f"routed to quarantine ({reason}) -> {csv_path or 'data/quarantine/error_log.json'}"
        )

    def finalize(self, final_status: str | None = None):
        if final_status:
            self.overall_status = final_status
        elif self.overall_status == "RUNNING":
            self.overall_status = "SUCCESS"

        manifest = {
            "run_id": self.run_id,
            "project_name": self.project_name,
            "started_at": self.started_at,
            "completed_at": datetime.now().isoformat(timespec="seconds"),
            "overall_status": self.overall_status,
            "total_stages": len(self.stages),
            "total_quarantined_rows": sum(q["rejected_count"] for q in self.quarantine_entries),
            "stages": self.stages,
            "quarantine_summary": self.quarantine_entries,
        }

        latest_path = os.path.join("data", "checkpoints", "run_latest.json")
        history_path = os.path.join("data", "checkpoints", f"run_{self.run_id}.json")

        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        error_log_path = os.path.join("data", "quarantine", "error_log.json")
        with open(error_log_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "run_id": self.run_id,
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                    "total_quarantined_rows": manifest["total_quarantined_rows"],
                    "exceptions": self.quarantine_entries,
                },
                f,
                indent=2,
            )

        return latest_path


def show_checkpoint(list_runs: bool = False, show_quarantine: bool = False, run_id: str | None = None):
    checkpoints_dir = os.path.join("data", "checkpoints")
    if not os.path.exists(checkpoints_dir):
        console.print("[yellow]No 'data/checkpoints/' directory found. Run 'analyst run' first.[/yellow]")
        return

    if list_runs:
        files = sorted(
            [f for f in os.listdir(checkpoints_dir) if f.startswith("run_") and f != "run_latest.json"],
            reverse=True,
        )
        if not files:
            console.print("[yellow]No checkpoint history found.[/yellow]")
            return

        t = Table(title="ETL Checkpoint Run History", header_style="bold magenta")
        t.add_column("Run ID", style="bold cyan")
        t.add_column("Completed At")
        t.add_column("Status")
        t.add_column("Stages")
        t.add_column("Quarantined Rows", justify="right")

        for fname in files:
            fpath = os.path.join(checkpoints_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                st = data.get("overall_status", "UNKNOWN")
                st_fmt = f"[green]{st}[/green]" if st == "SUCCESS" else f"[yellow]{st}[/yellow]"
                t.add_row(
                    data.get("run_id", fname),
                    data.get("completed_at", "-"),
                    st_fmt,
                    str(data.get("total_stages", 0)),
                    str(data.get("total_quarantined_rows", 0)),
                )
            except Exception:
                continue
        console.print(t)
        return

    target_file = (
        os.path.join(checkpoints_dir, f"run_{run_id}.json")
        if run_id
        else os.path.join(checkpoints_dir, "run_latest.json")
    )

    if not os.path.exists(target_file):
        console.print(f"[bold red]Checkpoint file not found:[/bold red] {target_file}")
        return

    with open(target_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    console.print(
        Panel.fit(
            f"[bold cyan]Pipeline Checkpoint Audit Report[/bold cyan]\n"
            f"Run ID: [bold]{manifest.get('run_id')}[/bold] | "
            f"Status: [bold green]{manifest.get('overall_status')}[/bold green] | "
            f"Completed: {manifest.get('completed_at')} | "
            f"Quarantined Rows: [bold yellow]{manifest.get('total_quarantined_rows', 0)}[/bold yellow]",
            border_style="cyan",
        )
    )

    stage_table = Table(
        title="Stage-by-Stage Audit Trail (WHAT, WHY, HOW)",
        show_header=True,
        header_style="bold magenta",
        show_lines=True,
    )
    stage_table.add_column("#", style="bold cyan", width=3)
    stage_table.add_column("Stage & Status", width=22)
    stage_table.add_column("WHAT Happened", width=32)
    stage_table.add_column("WHY It Happened", width=28)
    stage_table.add_column("HOW It Was Executed", width=28)

    for st in manifest.get("stages", []):
        status = st.get("status", "PASSED")
        badge = "[green][OK] PASSED[/green]" if status == "PASSED" else f"[yellow][!] {status}[/yellow]"
        stage_table.add_row(
            str(st.get("stage_num", "")),
            f"[bold]{st.get('stage_name', '')}[/bold]\n{badge}",
            st.get("what", ""),
            st.get("why", ""),
            st.get("how", ""),
        )

    console.print(stage_table)

    q_list = manifest.get("quarantine_summary", [])
    if show_quarantine or q_list:
        if not q_list:
            console.print("[green][OK] Zero quarantined records in this run.[/green]")
        else:
            q_table = Table(
                title="Quarantine / Exception Log (Daftar Pengecualian & Error Log)",
                show_header=True,
                header_style="bold red",
                show_lines=True,
            )
            q_table.add_column("Gate", style="bold yellow")
            q_table.add_column("Source Table", style="bold")
            q_table.add_column("Rejected Rows", justify="right")
            q_table.add_column("Rejection Reason (Why Rejected)")
            q_table.add_column("Quarantine Artifact")

            for q in q_list:
                q_table.add_row(
                    q.get("gate", ""),
                    q.get("source_table", ""),
                    str(q.get("rejected_count", 0)),
                    q.get("reason", ""),
                    q.get("csv_artifact", "data/quarantine/error_log.json"),
                )
            console.print(q_table)
