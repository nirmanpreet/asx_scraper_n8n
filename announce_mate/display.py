from typing import List, Dict
from rich.console import Console
from rich.table import Table
from rich import box
from rich.text import Text
from rich.live import Live
import random
import time
from .config import REQUEST_DELAY_MIN, REQUEST_DELAY_MAX
from .logger import logger

console = Console()


def display_announcements(items: List[Dict]):
    """Display a table of announcements."""
    try:
        if not items:
            console.print("[yellow]No new filtered announcements[/yellow]")
            return

        table = Table(show_header=True, header_style="bold magenta", box=box.SQUARE)
        table.add_column("Symbol", style="cyan")
        table.add_column("Headline", style="white")
        table.add_column("Date", style="green")
        table.add_column("Price Sensitive", style="bold")
        table.add_column("URL", style="blue")

        for item in items:
            ps_markup = "[red]YES[/red]" if item.get("isPriceSensitive") else "NO"
            url = item.get("url", "")
            table.add_row(
                item.get("symbol", ""),
                item.get("headline", ""),
                item.get("date", "").replace("T", " ").split(".")[0],
                ps_markup,
                url[:47] + "..." if len(url) > 50 else url
            )

        console.print("[bold green]New Filtered Announcements[/bold green]")
        console.print(table)

    except Exception as e:
        logger.error(f"Error displaying announcements: {e}")
        console.print(f"[red]Error displaying announcements: {e}[/red]")


def get_random_wait_time() -> int:
    """Return a random integer wait time from config."""
    try:
        return int(round(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)))
    except Exception as e:
        logger.error(f"Error generating random wait time: {e}")
        return int(REQUEST_DELAY_MIN)  # fallback


def wait_with_countdown(message: str = "Next check in"):
    """Show a countdown with a random wait time from config."""
    try:
        wait_time = get_random_wait_time()
        start_time = time.time()
        end_time = start_time + wait_time

        with Live(console=console, refresh_per_second=10) as live:
            while True:
                remaining = int(end_time - time.time())
                if remaining <= 0:
                    break
                live.update(Text(f"{message} {remaining} seconds"))
                time.sleep(0.1)
        return wait_time  # return the actual wait time if needed
    except Exception as e:
        logger.error(f"Error in countdown: {e}")
        console.print(f"[red]Countdown error: {e}[/red]")
        return 0
