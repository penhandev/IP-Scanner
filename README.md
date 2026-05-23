# Penhandev IP-Scanner

> **Languages:** **English** · [فارسی](README.fa.md)

[![Build and Release](https://github.com/penhandev/IP-Scanner/actions/workflows/release.yml/badge.svg)](https://github.com/penhandev/IP-Scanner/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A fast, cross-platform CLI tool to check the reachability of **IPs, CIDR blocks, IP ranges, domains, and URLs**.

## Features

- **Five input formats** — single IPs, CIDR (`1.0.0.0/24`), ranges (`1.0.0.1-1.0.0.50`), domains (`github.com`), full URLs (`https://api.github.com`)
- **Three check methods**:
  - `icmp` — classic ping (fast, default; also works on most non-rooted Android via unprivileged ICMP)
  - `tcp` — TCP connect on any port you pick (`-p`, default `443`; try `80` for plain HTTP)
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

### Easy way — just run it

```bash
python scanner.py
```

A menu pops up. Pick a file, pick a check method, press Enter. Done.

### Power-user way — command-line flags

```bash
python scanner.py -f targets.txt -m tcp -p 80
```

That line means: "use the file `targets.txt`, check with TCP, knock on port 80."

## All Options (Flags) — explained simply

Mix and match. You only need the ones you want.

### 1. Where do the targets come from? (pick one)

| Flag | Short | What it means |
|---|---|---|
| `--file FILE` | `-f` | "Read targets from this text file." Example: `-f cloudflare.txt` |
| `--target ...` | `-t` | "Use these targets I'm typing right now." Example: `-t 1.1.1.1 github.com 8.8.8.8` |
| `--input` | — | "Let me type targets one per line, then press Enter on an empty line when done." |

If you don't pass any of these, you get the friendly menu.

### 2. How should each target be checked?

| Flag | Short | What it means |
|---|---|---|
| `-m icmp` | — | Send a regular **ping**. Fastest. Doesn't work on most Android phones without root. |
| `-m tcp` | — | Try to **open a TCP connection** on a port. Works almost everywhere. |
| `-m http` | — | Send a tiny **HTTPS HEAD request**. Best for websites behind a CDN. |

### 3. Everything else

| Flag | Short | What it means |
|---|---|---|
| `--port PORT` | `-p` | Only matters with `-m tcp`. Which port to knock on. Default is `443` (HTTPS). Try `80` for plain HTTP. Example: `-p 80` |
| `--workers N` | `-w` | How many checks at the same time. Default `100`. Higher = faster but heavier. Example: `-w 200` |
| `--output FORMATS` | `-o` | Which result files to save. Pick any of `txt`, `json`, `csv`. Default is `txt`. Example: `-o txt json csv` |
| `--no-resolve` | — | "Don't bother looking up domain names." Faster but no IPs in the report. |
| `--verbose` | `-v` | Show extra info while running. Useful when something goes wrong. |
| `--version` | — | Just print the version and quit. |
| `--help` | `-h` | Show this whole list inside your terminal. |

### Quick recipes

```bash
# 1. Simplest — ping every IP in a file
python scanner.py -f targets.txt

# 2. Android-friendly — TCP on port 80, save all formats
python scanner.py -f cloudflare.txt -m tcp -p 80 -o txt json csv

# 3. Quick one-off — check three things right now
python scanner.py -t 1.1.1.1 8.8.8.8 github.com -m tcp

# 4. Type targets by hand
python scanner.py --input -m http

# 5. Big scan, faster — 300 workers
python scanner.py -f big_list.txt -w 300
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
