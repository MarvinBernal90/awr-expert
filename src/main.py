"""
Main Entry point for the AWR Expert CLI.
"""

import hashlib
from pathlib import Path

import typer
from rich.console import Console

from src.engine.health_score import HealthScoreOrchestrator
from src.parser.core import AWRParser
from src.services.db import initialize_warehouse
from src.services.repository import AWRRepository

console = Console()


def main(
    file: Path = typer.Option(
        ..., "--file", "-f", help="Path to the AWR HTML report file"
    ),
    save_to_db: bool = typer.Option(
        False, "--save-to-db", help="Persist the parsed metrics inside DuckDB"
    ),
) -> None:
    """Analyzes an Oracle AWR report and extracts telemetry metrics."""
    console.print("[bold blue]🚀 Starting AWR Expert[/bold blue]")

    if not file.exists():
        console.print(f"[bold red]Error: File {file} does not exist.[/bold red]")
        raise typer.Exit(code=1)

    console.print(f"📄 Analyzing file: [yellow]{file.name}[/yellow]\n")

    # 1. Parsing Phase
    parser = AWRParser()

    try:
        report = parser.parse(file)
    except Exception as e:
        console.print(f"[bold red]Error parsing report: {e}[/bold red]")
        raise typer.Exit(code=1)

    # Extract quick summary metrics to show the user
    db_id = report.db_info.db_id if report.db_info else "Unknown"
    db_name = report.db_info.db_name if report.db_info else "Unknown"
    version = report.db_info.version if report.db_info else "Unknown"
    host = report.db_info.host if report.db_info else "Unknown"
    elapsed = report.db_info.elapsed_time_min if report.db_info else 0.0

    db_cpu = report.time_model.db_cpu_s if report.time_model else "Unknown"
    os_cpus = report.os_stat.num_cpus if report.os_stat else "Unknown"

    console.print("[bold green]✔ Parsing successful![/bold green]")
    console.print(f"  • DB Name: [cyan]{db_name}[/cyan]")
    console.print(f"  • DB ID: [cyan]{db_id}[/cyan]")
    console.print(f"  • Release: [cyan]{version}[/cyan]")
    console.print(f"  • Host: [cyan]{host}[/cyan]")
    console.print(f"  • Physical OS CPUs: [cyan]{os_cpus}[/cyan]")
    console.print(f"  • Elapsed Time: [cyan]{elapsed} mins[/cyan]")
    console.print(f"  • DB CPU Consumed: [cyan]{db_cpu} s[/cyan]")
    console.print(f"  • Top Events Extracted: [cyan]{len(report.top_events)}[/cyan]")
    console.print(f"  • Top SQL Extracted: [cyan]{len(report.top_sql)}[/cyan]")
    console.print(f"  • Wait Histograms: [cyan]{len(report.wait_histograms)}[/cyan]")

    # 2. Storage Phase (Optional)
    if save_to_db:
        console.print("\n[bold blue]🗄️ Saving to DuckDB warehouse...[/bold blue]")
        initialize_warehouse()
        awr_hash = hashlib.sha256(file.read_bytes()).hexdigest()
        repo = AWRRepository()
        repo.save_report(awr_hash, report)
        console.print("[bold green]✔ Report saved safely![/bold green]")
        console.print(f"  • Idempotency Hash: [yellow]{awr_hash}[/yellow]")

    # 3. Expert Engine Analysis Phase
    orchestrator = HealthScoreOrchestrator(console)
    orchestrator.run_diagnostics(report)


if __name__ == "__main__":
    typer.run(main)
