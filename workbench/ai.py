import os
import json
import re
import requests
import duckdb
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from workbench.config import load_config

console = Console()

def get_database_schema(db_path: str) -> str:
    if not os.path.exists(db_path):
        return "No local DuckDB database found at " + db_path

    try:
        conn = duckdb.connect(db_path, read_only=True)
        tables = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()
        
        schema_text = []
        for (tbl,) in tables:
            desc = conn.execute(f"DESCRIBE {tbl}").fetchall()
            cols = [f"{col[0]} ({col[1]})" for col in desc]
            
            # Sample 2 rows
            samples = conn.execute(f"SELECT * FROM {tbl} LIMIT 2").fetchall()
            sample_str = f"Sample rows: {samples}" if samples else "No rows"

            schema_text.append(f"Table '{tbl}':\n  Columns: {', '.join(cols)}\n  {sample_str}")

        conn.close()
        return "\n\n".join(schema_text)
    except Exception as e:
        return f"Error reading schema: {e}"

def call_gemini(api_key: str, system_prompt: str, user_prompt: str) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_prompt}\n\nUser Question: {user_prompt}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }
    
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise Exception(f"Gemini API returned code {resp.status_code}: {resp.text}")
    
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)

def call_openai(api_key: str, system_prompt: str, user_prompt: str) -> dict:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise Exception(f"OpenAI API error {resp.status_code}: {resp.text}")
    data = resp.json()
    return json.loads(data["choices"][0]["message"]["content"])

def call_ollama(ollama_url: str, system_prompt: str, user_prompt: str) -> dict:
    url = f"{ollama_url.rstrip('/')}/api/generate"
    prompt = f"{system_prompt}\n\nRespond ONLY with valid JSON.\n\nUser Question: {user_prompt}"
    payload = {
        "model": "llama3.2",
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    resp = requests.post(url, json=payload, timeout=60)
    if resp.status_code != 200:
        raise Exception(f"Ollama error {resp.status_code}: {resp.text}")
    data = resp.json()
    return json.loads(data["response"])

def ask_ai(question: str, db_path: str = "data/analytics.duckdb"):
    cfg = load_config()
    provider = cfg.get("ai_provider", "gemini").lower()
    api_key = cfg.get("api_key") or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")

    if provider in ["gemini", "openai"] and not api_key:
        console.print(Panel(
            "[bold yellow]AI Configuration Required[/bold yellow]\n\n"
            f"Provider '{provider}' requires an API key.\n\n"
            "You can configure it via either method:\n"
            "  1. [bold cyan]analyst config --set-key <YOUR_API_KEY>[/bold cyan]\n"
            "  2. Or set environment variable: [bold cyan]$env:GEMINI_API_KEY = '<YOUR_KEY>'[/bold cyan]\n\n"
            "[dim]Note: You can also use local offline LLMs by switching to Ollama: 'analyst config --set-provider ollama'[/dim]",
            title="Setup AI",
            border_style="yellow"
        ))
        return

    schema_info = get_database_schema(db_path)
    
    system_prompt = f"""You are a Lead Data Analyst AI co-pilot.
The user is working in an open-source Data Analyst Workbench with DuckDB.
Database Schema and context:
{schema_info}

Analyze the user's business question. Produce a JSON response with exactly these fields:
{{
  "sql": "DuckDB SQL query to answer the question accurately",
  "explanation": "Short 1-2 sentence explanation of the logic",
  "business_insight": "Actionable takeaway on how the analyst should interpret the finding"
}}
Ensure the SQL uses standard DuckDB syntax."""

    console.print(f"[cyan]AI Analyst thinking on:[/cyan] [italic]{question}[/italic]...")
    
    try:
        if provider == "gemini":
            result = call_gemini(api_key, system_prompt, question)
        elif provider == "openai":
            result = call_openai(api_key, system_prompt, question)
        elif provider == "ollama":
            result = call_ollama(cfg.get("ollama_url", "http://localhost:11434"), system_prompt, question)
        else:
            console.print(f"[bold red]Unsupported provider:[/bold red] {provider}")
            return
    except Exception as e:
        console.print(f"[bold red]AI Request Failed:[/bold red] {e}")
        return

    sql_query = result.get("sql", "").strip()
    explanation = result.get("explanation", "")
    insight = result.get("business_insight", "")

    # Display generated SQL
    console.print(Panel(
        Syntax(sql_query, "sql", theme="monokai", line_numbers=False),
        title=f"Generated SQL ({explanation})",
        border_style="blue"
    ))

    # Execute on DuckDB
    if sql_query and os.path.exists(db_path):
        console.print("[dim]Executing query on DuckDB...[/dim]")
        try:
            conn = duckdb.connect(db_path, read_only=True)
            rel = conn.sql(sql_query)
            rows = rel.fetchall()
            cols = rel.columns
            conn.close()

            table = Table(title=f"Query Result ({len(rows)} rows)", show_header=True, header_style="bold cyan")
            for c in cols:
                table.add_column(str(c))
            for r in rows[:20]:
                table.add_row(*[str(val) if val is not None else "[dim]NULL[/dim]" for val in r])

            console.print(table)
            if len(rows) > 20:
                console.print(f"[dim](Showing first 20 rows of {len(rows)})[/dim]")

            if insight:
                console.print(Panel(insight, title="💡 Business Takeaway", border_style="green"))

        except Exception as e:
            console.print(f"[bold red]Query Execution Error:[/bold red] {e}")
    else:
        console.print(f"[yellow]Could not execute: database {db_path} not found.[/yellow]")
