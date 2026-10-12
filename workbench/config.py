import os
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

CONFIG_DIR = os.path.expanduser("~/.analyst_workbench")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_PROJECTS_DIR = os.path.expanduser("~/AnalystProjects")

DEFAULT_CONFIG = {
    "projects_dir": DEFAULT_PROJECTS_DIR,
    "default_template": "restaurant-sales",
    "ai_provider": "gemini",
    "api_key": "",
    "ollama_url": "http://localhost:11434"
}

def load_config() -> dict:
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            # Ensure all default keys exist
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(cfg: dict):
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def set_config_value(key: str, value: str):
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
    console.print(f"[bold green][OK][/bold green] Set [cyan]{key}[/cyan] = [yellow]{value}[/yellow]")

def print_config():
    cfg = load_config()
    console.print(Panel.fit("[bold cyan]Workbench Configuration[/bold cyan]", border_style="cyan"))

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="bold")
    table.add_column("Current Value")
    table.add_column("Description")

    key_display = "***" + cfg["api_key"][-4:] if len(cfg.get("api_key", "")) > 4 else ("(not set)" if not cfg.get("api_key") else "***")

    table.add_row("projects_dir", cfg.get("projects_dir"), "Default parent folder for new projects")
    table.add_row("default_template", cfg.get("default_template"), "Default template for 'analyst new'")
    table.add_row("ai_provider", cfg.get("ai_provider"), "AI provider (gemini, openai, ollama)")
    table.add_row("api_key", key_display, "API key for AI provider (or set via env var)")
    table.add_row("ollama_url", cfg.get("ollama_url"), "Local Ollama server URL")

    console.print(table)
    console.print("[dim]Use 'analyst config --set-dir <path>' to change default folder.[/dim]")
    console.print("[dim]Use 'analyst config --set-key <key>' to configure AI API key.[/dim]\n")
