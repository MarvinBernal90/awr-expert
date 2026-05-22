"""
Main Entry point for the AWR Expert CLI.
"""

import hashlib
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.engine.cpu import analyze_cpu
from src.engine.io import analyze_io
from src.engine.memory import analyze_memory
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
    console.print("\n[bold blue]🧠 Running Expert AI Diagnostics...[/bold blue]")

    # Run all heuristic engines
    cpu_diagnosis = analyze_cpu(report)
    io_diagnosis = analyze_io(report)
    memory_diagnosis = analyze_memory(report)

    # Filter out engines that skipped due to lack of specific data
    active_diagnoses = [d for d in (cpu_diagnosis, io_diagnosis, memory_diagnosis) if d]

    if active_diagnoses:
        # Build Health Score Table
        table = Table(
            title="[bold]OVERALL HEALTH SCORE (Executive Summary)[/bold]",
            show_header=True,
            header_style="bold white",
        )
        table.add_column("Area", style="cyan", justify="left")
        table.add_column("Status", style="white", justify="left")
        table.add_column("Severity", justify="center")
        table.add_column("Impact", justify="center")

        for diag in active_diagnoses:
            # Determine color based on severity
            sev_color = "bold green"
            if diag.severity == "WARN":
                sev_color = "bold yellow"
            elif diag.severity == "CRITICAL":
                sev_color = "bold red"

            table.add_row(
                diag.area,
                diag.status,
                f"[{sev_color}]{diag.severity}[/{sev_color}]",
                diag.impact,
            )

        console.print("\n")
        console.print(table)

        # Print Root Causes / Evidences
        all_findings = [f for d in active_diagnoses for f in d.findings]
        if all_findings:
            console.print("\n[bold red]🔍 TOP ROOT CAUSES / Evidence:[/bold red]")
            for finding in all_findings:
                icon = "🔴" if finding.is_critical else "ℹ️"
                console.print(f"  {icon} [white]{finding.description}[/white]")

        # Print Recommendations
        console.print("\n[bold green]💡 Expert Recommendations:[/bold green]")
        for diag in active_diagnoses:
            console.print(
                Panel(
                    diag.recommendation,
                    title=f"[bold]{diag.area}[/bold]",
                    border_style="green",
                )
            )
    else:
        # Fallback message when no engine generates a diagnosis
        console.print(
            "\n[bold yellow]ℹ No actionable diagnoses generated "
            "(insufficient engine data).[/bold yellow]"
        )


if __name__ == "__main__":
    typer.run(main)
