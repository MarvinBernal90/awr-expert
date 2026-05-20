"""
Command Line Interface for AWR Expert.
"""
import logging
from pathlib import Path

import typer
from rich.console import Console

from src.parser.core import AWRParser
from src.services.db import DBManager
from src.services.repository import AWRRepository

# Setup basic logging to avoid cluttering the beautiful CLI output
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
# We can still capture parser logs if needed, but we keep the CLI clean.

app = typer.Typer(
    help="AWR Expert CLI - The intelligent parser for Oracle AWR reports.",
    add_completion=False,
)
console = Console()


@app.command()
def parse(
    file: Path = typer.Option(
        ...,
        "--file",
        "-f",
        help="Path to the AWR HTML file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    save_to_db: bool = typer.Option(
        False,
        "--save-to-db",
        "-s",
        help="Save the parsed report to the DuckDB warehouse",
    ),
) -> None:
    """
    Parses an Oracle AWR HTML report and optionally saves it to the database.
    """
    console.print("[bold blue]🚀 Starting AWR Expert[/bold blue]")
    console.print(f"📄 Analyzing file: [bold green]{file}[/bold green]")

    try:
        # 1. Parse the HTML file
        parser = AWRParser()
        report = parser.parse(file)

        # Extract some quick summary metrics to show the user
        db_id = report.db_info.db_id if report.db_info else "Unknown"
        elapsed = report.db_info.elapsed_time_min if report.db_info else 0.0
        
        console.print("\n[bold green]✔ Parsing successful![/bold green]")
        console.print(f"  • DB ID: [cyan]{db_id}[/cyan]")
        console.print(f"  • Elapsed Time: [cyan]{elapsed} mins[/cyan]")
        console.print(f"  • Top Events Extracted: [cyan]{len(report.top_events)}[/cyan]")
        console.print(f"  • Top SQL Extracted: [cyan]{len(report.top_sql)}[/cyan]")
        
        if report.metadata.parser_warnings:
            console.print(f"\n[bold yellow]⚠ Warnings ({len(report.metadata.parser_warnings)}):[/bold yellow]")
            for w in report.metadata.parser_warnings:
                console.print(f"  - {w}")

        # 2. Save to database if the flag is present
        if save_to_db:
            console.print("\n[bold magenta]🗄️ Saving to DuckDB warehouse...[/bold magenta]")
            db_manager = DBManager()
            db_manager.initialize_schema()
            repo = AWRRepository(db_manager)
            
            awr_hash = repo.save(report)
            console.print("[bold green]✔ Report saved safely![/bold green]")
            console.print(f"  • Idempotency Hash: [dim]{awr_hash}[/dim]")

    except Exception as e:
        console.print(f"\n[bold red]✘ Error processing AWR file:[/bold red] {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()