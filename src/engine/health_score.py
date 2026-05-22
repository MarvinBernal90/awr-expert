"""
Health Score Orchestrator.
Consolidates diagnostics from all vertical engines and renders the Executive Dashboard.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.engine.cpu import analyze_cpu
from src.engine.io import analyze_io
from src.engine.memory import analyze_memory
from src.models.base import AWRReport


class HealthScoreOrchestrator:
    """Runs all heuristic engines and orchestrates the visual output."""

    def __init__(self, console: Console):
        """Initializes the orchestrator with a rich console instance."""
        self.console = console

    def run_diagnostics(self, report: AWRReport) -> None:
        """Executes engines and renders the Executive Dashboard."""
        self.console.print(
            "\n[bold blue]🧠 Running Expert AI Diagnostics...[/bold blue]"
        )

        # 1. Run all heuristic engines
        cpu_diagnosis = analyze_cpu(report)
        io_diagnosis = analyze_io(report)
        memory_diagnosis = analyze_memory(report)

        # 2. Filter out skipped engines
        active_diagnoses = [
            d for d in (cpu_diagnosis, io_diagnosis, memory_diagnosis) if d
        ]

        if not active_diagnoses:
            self.console.print(
                "\n[bold yellow]ℹ No actionable diagnoses generated "
                "(insufficient engine data).[/bold yellow]"
            )
            return

        # 3. Build and print the Health Score Table
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

        self.console.print("\n")
        self.console.print(table)

        # 4. Print Root Causes / Evidence (Sorted by criticality)
        all_findings = sorted(
            (f for d in active_diagnoses for f in d.findings),
            key=lambda finding: not finding.is_critical,
        )

        if all_findings:
            self.console.print("\n[bold red]🔍 TOP ROOT CAUSES / Evidence:[/bold red]")
            for finding in all_findings:
                icon = "🔴" if finding.is_critical else "ℹ️"
                self.console.print(f"  {icon} [white]{finding.description}[/white]")

        # 5. Print Expert Recommendations
        self.console.print("\n[bold green]💡 Expert Recommendations:[/bold green]")
        for diag in active_diagnoses:
            self.console.print(
                Panel(
                    diag.recommendation,
                    title=f"[bold]{diag.area}[/bold]",
                    border_style="green",
                )
            )
