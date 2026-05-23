"""Rich-based UI helpers — banners, prompts, menus."""

from __future__ import annotations

import os
import platform

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

console = Console()

_IS_WINDOWS = platform.system().lower() == "windows"


def clear_screen() -> None:
    os.system("cls" if _IS_WINDOWS else "clear")


def show_banner(version: str) -> None:
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]Penhandev IP-Scanner v{version}[/bold cyan]\n"
            f"[green]IP / CIDR / Range / Domain / URL[/green]"
        )
    )


def show_file_menu(files: list[str]) -> str | None:
    """Show a numbered menu. Return the chosen filename, ``None`` to exit,
    or an empty string if the input was invalid (caller should retry)."""
    table = Table(show_header=False, box=None, padding=(0, 1))
    for i, name in enumerate(files, start=1):
        table.add_row(f"[cyan]{i}[/cyan]", name)
    table.add_row("[red]0[/red]", "Exit")
    console.print("\n[bold]Available files:[/bold]")
    console.print(table)

    choice = Prompt.ask("\nChoose a file").strip()
    if choice == "0":
        return None
    try:
        idx = int(choice) - 1
    except ValueError:
        console.print("[red]Invalid choice.[/red]")
        return ""
    if 0 <= idx < len(files):
        return files[idx]
    console.print("[red]Out of range.[/red]")
    return ""


def show_method_menu() -> str:
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_row("[cyan]1[/cyan]", "ICMP ping  [dim](classic, fast)[/dim]")
    table.add_row("[cyan]2[/cyan]", "TCP        [dim](choose a port; works when ICMP is blocked)[/dim]")
    table.add_row("[cyan]3[/cyan]", "HTTPS HEAD [dim](best for CDN-fronted hosts)[/dim]")
    console.print("\n[bold]Check method:[/bold]")
    console.print(table)

    choice = Prompt.ask("Choose method", default="1").strip()
    return {"1": "icmp", "2": "tcp", "3": "http"}.get(choice, "icmp")


def prompt_tcp_port(default: int = 443) -> int:
    """Ask the user which TCP port to probe. 443 = HTTPS, 80 = HTTP."""
    while True:
        raw = Prompt.ask(
            "TCP port [dim](443=HTTPS, 80=HTTP)[/dim]",
            default=str(default),
        ).strip()
        try:
            port = int(raw)
        except ValueError:
            console.print("[red]Port must be a number.[/red]")
            continue
        if 1 <= port <= 65535:
            return port
        console.print("[red]Port must be between 1 and 65535.[/red]")


def confirm(prompt: str, default: str = "y") -> bool:
    return Prompt.ask(prompt, choices=["y", "n"], default=default).lower() == "y"


def pause() -> None:
    Prompt.ask("\nPress Enter to continue", default="")
