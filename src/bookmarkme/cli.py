"""CLI entry point for BookmarkMe."""

from __future__ import annotations

import os
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from bookmarkme.organizer import organize_bookmarks
from bookmarkme.parser import (
    count_bookmarks,
    generate_bookmarks_html,
    parse_bookmarks,
)

console = Console()
app = typer.Typer(
    name="bookmarkme",
    help="🔖 AI-powered bookmark organizer — beautify and reorganize your bookmarks with Gemini.",
    add_completion=False,
    rich_markup_mode="rich",
    invoke_without_command=True,
)


@app.callback(invoke_without_command=True)
def organize(
    input_file: Path = typer.Option(
        Path("bookmarks/bookmarks.html"),
        "--input",
        "-i",
        help="Path to the HTML bookmark file to organize.",
        exists=True,
        readable=True,
    ),
    output_file: Path = typer.Option(
        Path("bookmarks/bookmarks_organized.html"),
        "--output",
        "-o",
        help="Path for the organized bookmark HTML output.",
    ),
    model: str = typer.Option(
        "gemini-2.5-pro",
        "--model",
        "-m",
        help="Gemini model to use for organization.",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Google AI API key. Defaults to GEMINI_API_KEY from .env or environment.",
    ),
    no_cache: bool = typer.Option(
        False,
        "--no-cache",
        help="Bypass the local category cache and re-categorize all bookmarks.",
    ),
) -> None:
    """Organize and beautify an HTML bookmark file using Gemini AI.

    Reads your exported bookmarks, sends them to Gemini for intelligent
    reorganization, and generates a clean HTML file ready to re-import.
    """
    # Load .env file (if present)
    load_dotenv()

    # Resolve API key: --api-key flag > .env / environment variable
    resolved_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not resolved_key:
        console.print(
            Panel(
                "[bold red]No API key found![/bold red]\n\n"
                "Set the [bold]GEMINI_API_KEY[/bold] environment variable or pass "
                "[bold]--api-key[/bold].\n\n"
                "Get a free key at [link=https://aistudio.google.com]aistudio.google.com[/link]",
                title="❌ Missing API Key",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    # Read input file
    console.print(f"\n[bold]📂 Reading bookmarks from:[/bold] {input_file}")
    try:
        html_content = input_file.read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[bold red]❌ Failed to read input file: {e}[/bold red]")
        raise typer.Exit(code=1) from e

    # Parse bookmarks
    with console.status("[bold blue]Parsing bookmarks...[/bold blue]"):
        bookmarks = parse_bookmarks(html_content)

    bookmark_count = count_bookmarks(bookmarks)
    if bookmark_count == 0:
        console.print("[bold yellow]⚠️  No bookmarks found in the file![/bold yellow]")
        raise typer.Exit(code=1)

    console.print(f"[bold green]✅ Found {bookmark_count} bookmarks[/bold green]")

    # Organize with Gemini
    try:
        organized = organize_bookmarks(bookmarks, resolved_key, model, use_cache=not no_cache)
    except (ValueError, RuntimeError) as e:
        console.print(f"\n[bold red]❌ Organization failed: {e}[/bold red]")
        raise typer.Exit(code=1) from e

    # Generate output HTML
    with console.status("[bold blue]Generating organized HTML...[/bold blue]"):
        output_html = generate_bookmarks_html(organized)

    # Write output
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(output_html, encoding="utf-8")
    except Exception as e:
        console.print(f"[bold red]❌ Failed to write output file: {e}[/bold red]")
        raise typer.Exit(code=1) from e

    def format_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"

    in_size = format_size(input_file.stat().st_size)
    out_size = format_size(output_file.stat().st_size)

    organized_count = count_bookmarks(organized)
    console.print(
        Panel(
            f"[bold green]Bookmarks organized successfully![/bold green]\n\n"
            f"📥 Input:  {input_file} ({in_size}, {bookmark_count} bookmarks)\n"
            f"📤 Output: {output_file} ({out_size}, {organized_count} bookmarks)\n\n"
            f"Import the output file into your browser to use the organized bookmarks.",
            title="🎉 Done!",
            border_style="green",
        )
    )

