"""Export scan results to TXT, JSON, or CSV.

The TXT format is kept backwards-compatible with v2: one alive target per
line, using the original input string. JSON and CSV contain richer info.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from .checker import CheckResult


def _stem(source_file: str) -> str:
    return Path(source_file).stem


# ---------------------------------------------------------------------------

def export_txt(results: List[CheckResult], source_file: str, output_dir: str = ".") -> str:
    """Write alive targets, one per line (original input preserved)."""
    path = Path(output_dir) / f"results_{_stem(source_file)}.txt"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in results:
            if r.alive:
                f.write(f"{r.target.output_label}\n")
    return str(path)


def export_json(results: List[CheckResult], source_file: str, output_dir: str = ".") -> str:
    path = Path(output_dir) / f"results_{_stem(source_file)}.json"
    payload = {
        "source": source_file,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total": len(results),
        "alive": sum(1 for r in results if r.alive),
        "results": [
            {
                "original": r.target.original,
                "host": r.target.host,
                "ip": r.target.ip,
                "alive": r.alive,
                "latency_ms": round(r.latency_ms, 2) if r.latency_ms is not None else None,
                "method": r.method,
                "error": r.error,
            }
            for r in results
        ],
    }
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return str(path)


def export_csv(results: List[CheckResult], source_file: str, output_dir: str = ".") -> str:
    path = Path(output_dir) / f"results_{_stem(source_file)}.csv"
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["original", "host", "ip", "alive", "latency_ms", "method", "error"])
        for r in results:
            writer.writerow([
                r.target.original,
                r.target.host,
                r.target.ip or "",
                "yes" if r.alive else "no",
                f"{r.latency_ms:.2f}" if r.latency_ms is not None else "",
                r.method,
                r.error or "",
            ])
    return str(path)


# ---------------------------------------------------------------------------

_EXPORTERS = {
    "txt": export_txt,
    "json": export_json,
    "csv": export_csv,
}


def export(
    results: Iterable[CheckResult],
    source_file: str,
    formats: Iterable[str],
    output_dir: str = ".",
) -> List[str]:
    """Run every requested exporter and return the list of paths written."""
    results = list(results)
    written: List[str] = []
    for fmt in formats:
        fn = _EXPORTERS.get(fmt)
        if fn is None:
            continue
        written.append(fn(results, source_file, output_dir))
    return written
