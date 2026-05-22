"""Penhandev IP-Scanner — main entry point.

Examples:
    # Interactive menu (pick a .txt file):
    python scanner.py

    # Scan from a file:
    python scanner.py -f targets.txt -m tcp

    # Inline targets via -t (supports all formats):
    python scanner.py -t 8.8.8.8 github.com 1.0.0.0/24 10.0.0.1-10.0.0.5

    # Interactive input mode (type targets one per line):
    python scanner.py --input -m http

    # Multi-format output:
    python scanner.py -f targets.txt -o txt json csv

Termux / Android:
    No root  → use -m tcp or -m http (default is tcp automatically)
    Rooted   → pick icmp, scanner will request su automatically
"""

from __future__ import annotations

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)

from ipscanner import __version__, checker, exporter, parser
from ipscanner.checker import IS_ANDROID, IS_ROOT, has_su, relaunch_as_root
from ipscanner.ui import (
    clear_screen,
    confirm,
    console,
    pause,
    show_banner,
    show_file_menu,
    show_method_menu,
)

log = logging.getLogger("ipscanner")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def list_txt_files() -> list[str]:
    return sorted(
        f.name
        for f in Path(".").iterdir()
        if f.is_file()
        and f.suffix == ".txt"
        and not f.name.startswith("results_")
    )


def _handle_android_icmp() -> bool:
    """Gate for ICMP on Android. Returns True → proceed, False → abort."""
    if IS_ROOT:
        return True

    console.print("\n[bold yellow]⚠  Android detected — ICMP needs root[/bold yellow]")
    console.print("[cyan]Checking for root access (su)...[/cyan]")
    root_available = has_su()

    if root_available:
        console.print("[green]✓ Root (su) is available on this device.[/green]")
        if confirm("Re-launch scanner with root to enable ICMP?"):
            console.print("[cyan]Re-launching as root... (superuser prompt may appear)[/cyan]\n")
            relaunch_as_root()  # never returns
        else:
            console.print("[yellow]Tip: use [bold]-m tcp[/bold] or [bold]-m http[/bold] instead.[/yellow]")
            return False
    else:
        console.print(
            "[red]✗ Root (su) not found or not granted.[/red]\n"
            "  [green]Use [bold]-m tcp[/bold] or [bold]-m http[/bold] instead.[/green]"
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Input mode: interactive multi-line entry
# ---------------------------------------------------------------------------

def collect_targets_interactively() -> list[parser.Target]:
    """Prompt the user to enter targets one per line until an empty line."""
    console.print(
        "\n[bold cyan]Enter targets[/bold cyan] "
        "[dim](one per line — IP, CIDR, range, domain, URL)[/dim]"
    )
    console.print("[dim]Press Enter on an empty line when done.[/dim]\n")

    raw_lines: list[str] = []
    while True:
        try:
            line = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            # Ctrl-D / Ctrl-C → treat as end of input
            break
        if not line:
            break
        raw_lines.append(line)

    if not raw_lines:
        return []

    targets: list[parser.Target] = []
    seen: set[tuple] = set()
    for line in raw_lines:
        for t in parser.parse_line(line):
            key = (t.host, t.ip)
            if key not in seen:
                seen.add(key)
                targets.append(t)
    return targets


# ---------------------------------------------------------------------------
# Core scan runner — accepts a list of targets directly
# ---------------------------------------------------------------------------

def _execute_scan(
    targets: list[parser.Target],
    method: str,
    workers: int,
    resolve_dns: bool,
    output_label: str,
    formats: tuple[str, ...],
) -> None:
    """Run the scan on an already-built target list."""
    if IS_ANDROID and method == "icmp":
        if not _handle_android_icmp():
            return

    if not targets:
        console.print("[red]No valid targets found.[/red]")
        return

    if resolve_dns and any(t.ip is None for t in targets):
        console.print("[cyan]Resolving hostnames...[/cyan]")
        targets = parser.resolve_all(targets)

    total = len(targets)
    unresolved = sum(1 for t in targets if t.ip is None)
    msg = f"[green]Loaded {total:,} targets[/green]"
    if unresolved:
        msg += f" [yellow]({unresolved:,} unresolved)[/yellow]"
    console.print(msg)

    if not confirm(f"Start scan of {total:,} targets with method=[bold]{method}[/bold]?"):
        return

    results: list[checker.CheckResult] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Scanning", total=total)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(checker.check, t, method=method): t for t in targets}
            for fut in as_completed(futures):
                try:
                    res = fut.result()
                except Exception as e:
                    log.exception("Checker crashed: %s", e)
                    continue
                results.append(res)
                progress.update(task, advance=1)

    alive = [r for r in results if r.alive]
    console.print(
        f"\n[bold green]Alive: {len(alive):,}[/bold green]  /  "
        f"[bold red]Dead: {len(results) - len(alive):,}[/bold red]"
    )

    if alive:
        console.print("\n[bold]Alive targets:[/bold]")
        alive_sorted = sorted(
            alive, key=lambda r: r.latency_ms if r.latency_ms is not None else float("inf")
        )
        for r in alive_sorted[:20]:
            lat = f"  [dim]{r.latency_ms:.0f} ms[/dim]" if r.latency_ms is not None else ""
            console.print(f"  [green]+[/green] {r.target.display}{lat}")
        if len(alive_sorted) > 20:
            console.print(f"  [dim]... and {len(alive_sorted) - 20:,} more (see results file)[/dim]")

    for path in exporter.export(results, output_label, formats):
        console.print(f"[green]Saved:[/green] {path}")


# ---------------------------------------------------------------------------
# Public wrappers (file / inline / interactive)
# ---------------------------------------------------------------------------

def run_scan_from_file(
    source_file: str,
    method: str = "icmp",
    workers: int = 100,
    formats: tuple[str, ...] = ("txt",),
    resolve_dns: bool = True,
) -> None:
    console.print(f"\n[cyan]Loading targets from[/cyan] {source_file}...")
    try:
        targets = parser.load_targets(source_file)
    except FileNotFoundError:
        console.print(f"[red]File not found: {source_file}[/red]")
        return
    except OSError as e:
        console.print(f"[red]Could not read file: {e}[/red]")
        return
    _execute_scan(targets, method, workers, resolve_dns, source_file, formats)


def run_scan_from_args(
    raw_targets: list[str],
    method: str = "icmp",
    workers: int = 100,
    formats: tuple[str, ...] = ("txt",),
    resolve_dns: bool = True,
) -> None:
    """Parse targets passed directly as CLI arguments (-t / --target)."""
    targets: list[parser.Target] = []
    seen: set[tuple] = set()
    for raw in raw_targets:
        for t in parser.parse_line(raw):
            key = (t.host, t.ip)
            if key not in seen:
                seen.add(key)
                targets.append(t)

    if not targets:
        console.print("[red]No valid targets in the provided arguments.[/red]")
        return

    console.print(f"\n[cyan]Parsed[/cyan] {len(targets):,} target(s) from arguments.")
    _execute_scan(targets, method, workers, resolve_dns, "inline_targets", formats)


def run_scan_from_input(
    method: str = "icmp",
    workers: int = 100,
    formats: tuple[str, ...] = ("txt",),
    resolve_dns: bool = True,
) -> None:
    """Collect targets interactively (--input mode)."""
    targets = collect_targets_interactively()
    if not targets:
        console.print("[red]No targets entered.[/red]")
        return
    console.print(f"\n[cyan]Parsed[/cyan] {len(targets):,} target(s).")
    _execute_scan(targets, method, workers, resolve_dns, "inline_targets", formats)


# ---------------------------------------------------------------------------
# Interactive menu (no CLI flags)
# ---------------------------------------------------------------------------

def interactive_mode() -> None:
    if IS_ANDROID and not IS_ROOT:
        show_banner(__version__)
        console.print(
            "\n[bold yellow]⚠  Running on Android / Termux[/bold yellow]\n"
            "   ICMP ping is [red]not available[/red] without root.\n"
            "   Please select [bold]TCP[/bold] or [bold]HTTPS[/bold] as your check method.\n"
            "   (If your device is rooted, pick ICMP — scanner will request su.)\n"
        )
        pause()

    while True:
        clear_screen()
        show_banner(__version__)

        # Show source options
        console.print("\n[bold]Input source:[/bold]")
        console.print("  [cyan]1[/cyan] - Load from a .txt file")
        console.print("  [cyan]2[/cyan] - Enter targets manually")
        console.print("  [red]0[/red] - Exit\n")

        from rich.prompt import Prompt
        choice = Prompt.ask("Choose").strip()

        if choice == "0":
            return

        elif choice == "1":
            files = list_txt_files()
            if not files:
                console.print("\n[red]No .txt files found in the current directory.[/red]")
                console.print("[dim]Place a targets.txt next to scanner.py and try again.[/dim]")
                pause()
                continue

            chosen = show_file_menu(files)
            if chosen is None:
                return
            if chosen == "":
                pause()
                continue

            method = show_method_menu()
            run_scan_from_file(chosen, method=method)
            pause()

        elif choice == "2":
            method = show_method_menu()
            run_scan_from_input(method=method)
            pause()

        else:
            continue


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    default_method = "tcp" if (IS_ANDROID and not IS_ROOT) else "icmp"

    ap = argparse.ArgumentParser(
        prog="scanner",
        description="Penhandev IP / Domain / URL scanner.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
input sources (pick one):
  -f FILE           scan targets from a .txt file
  -t TARGET ...     scan targets passed directly as arguments
  --input           enter targets interactively (one per line)
  (none)            open the interactive menu

target formats supported everywhere:
  8.8.8.8                single IP
  1.0.0.0/24             CIDR block
  10.0.0.1-10.0.0.50     IPv4 range
  github.com             domain
  https://api.github.com URL

Android/Termux:
  no root  → default method is tcp
  rooted   → pick icmp, scanner requests su automatically
        """,
    )

    src = ap.add_mutually_exclusive_group()
    src.add_argument("-f", "--file", help="Target file.")
    src.add_argument(
        "-t", "--target",
        nargs="+",
        metavar="TARGET",
        help="One or more targets inline (IPs, CIDRs, ranges, domains, URLs).",
    )
    src.add_argument(
        "--input",
        action="store_true",
        help="Enter targets interactively, one per line.",
    )

    ap.add_argument(
        "-m", "--method",
        choices=["icmp", "tcp", "http"],
        default=default_method,
        help=f"Check method (default on this device: {default_method}).",
    )
    ap.add_argument(
        "-w", "--workers",
        type=int, default=100,
        help="Concurrent workers (default: 100).",
    )
    ap.add_argument(
        "-o", "--output",
        nargs="+",
        choices=["txt", "json", "csv"],
        default=["txt"],
        help="Output format(s) (default: txt).",
    )
    ap.add_argument("--no-resolve", action="store_true", help="Skip DNS resolution.")
    ap.add_argument("-v", "--verbose", action="store_true", help="Verbose logging.")
    ap.add_argument("--version", action="version", version=f"Penhandev IP-Scanner v{__version__}")

    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        show_banner(__version__)

        if args.file:
            run_scan_from_file(
                args.file,
                method=args.method,
                workers=args.workers,
                formats=tuple(args.output),
                resolve_dns=not args.no_resolve,
            )
        elif args.target:
            run_scan_from_args(
                args.target,
                method=args.method,
                workers=args.workers,
                formats=tuple(args.output),
                resolve_dns=not args.no_resolve,
            )
        elif args.input:
            run_scan_from_input(
                method=args.method,
                workers=args.workers,
                formats=tuple(args.output),
                resolve_dns=not args.no_resolve,
            )
        else:
            interactive_mode()

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())