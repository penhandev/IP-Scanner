# Penhandev IP-Scanner

> **Languages:** **English** · [فارسی](README.fa.md)

[![Build and Release](https://github.com/penhandev/IP-Scanner/actions/workflows/release.yml/badge.svg)](https://github.com/penhandev/IP-Scanner/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A fast, cross-platform CLI tool to check the reachability of **IPs, CIDR blocks, IP ranges, domains, and URLs**.

## Features

- **Five input formats** — single IPs, CIDR (`1.0.0.0/24`), ranges (`1.0.0.1-1.0.0.50`), domains (`github.com`), full URLs (`https://api.github.com`)
- **Three check methods**:
  - `icmp` — classic ping (fast, default)
  - `tcp` — TCP connect on port 443 (works when ICMP is filtered)
  - `http` — HTTPS `HEAD` request (best for CDN-fronted hosts)
- **Cross-platform** — Windows, Linux, macOS
- **Latency measurement** for each alive host
- **Concurrent scanning** (100 workers by default, configurable)
- **Multiple output formats** — TXT, JSON, CSV
- **Two modes** — interactive menu *or* non-interactive CLI flags
- **Original input preserved** in output (your `github.com` stays `github.com`, not just the resolved IP)

## Install

```bash
git clone https://github.com/penhandev/IP-Scanner.git
cd IP-Scanner
pip install -r requirements.txt
```

Requires **Python 3.10+**.

## Usage

### Interactive (legacy v2 flow)

```bash
python scanner.py
```

The scanner lists every `*.txt` file in the current directory and lets you pick one.

### Command-line

```bash
python scanner.py -f targets.txt                       # ICMP ping
python scanner.py -f targets.txt -m tcp                # TCP :443
python scanner.py -f targets.txt -m http               # HTTPS HEAD
python scanner.py -f targets.txt -o txt json csv       # multi-format export
python scanner.py -f targets.txt -w 200                # 200 workers
python scanner.py --help                               # full options
```

### Input file format

```text
# Lines starting with '#' are ignored, blank lines too.

# Single IPs
8.8.8.8
1.1.1.1

# CIDR blocks
192.168.1.0/24

# IPv4 ranges
10.0.0.1-10.0.0.50

# Domains
github.com
www.cloudflare.com

# URLs (any scheme / path is fine)
https://api.github.com/v3
http://example.com/something
```

## Output

For input `targets.txt`, the tool writes:

- `results_targets.txt` — alive targets, one per line (original input)
- `results_targets.json` — full results with latency, errors, method
- `results_targets.csv` — same data, spreadsheet-friendly

Only formats passed to `-o` are produced; the default is `txt` only.

## Project layout

```text
IP-Scanner/
├── scanner.py              # entry point (menu + argparse)
├── ipscanner/
│   ├── __init__.py
│   ├── parser.py           # input parsing (CIDR / range / URL / domain)
│   ├── checker.py          # ICMP / TCP / HTTP probes
│   ├── exporter.py         # TXT / JSON / CSV writers
│   └── ui.py               # Rich helpers
├── targets.txt             # sample input (also: akami.txt, amazon.txt, cloudflare.txt, fastly.txt)
├── .github/workflows/      # automated build & release pipeline
├── requirements.txt
├── .gitignore
└── LICENSE
```

## Roadmap

- [ ] async backend (`asyncio` + `aiohttp`) for 10× speedup on large lists
- [ ] reverse DNS lookup on alive IPs
- [ ] GeoIP / ASN tagging
- [ ] resume-on-interrupt (partial result file)
- [ ] config file (`.toml`) for default flags

## Disclaimer

This tool performs **read-only connectivity checks**. Only scan hosts you own or are authorized to assess.

## License

MIT — see [LICENSE](LICENSE).
