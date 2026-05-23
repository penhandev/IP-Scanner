# Penhandev IP-Scanner

> **زبان‌ها:** [English](README.md) · **فارسی**

<div dir="rtl">

ابزار سریع و چندسکویی برای بررسی در دسترس بودن **آی‌پی‌ها، CIDR، رنج‌های IP، دامنه‌ها و URL ها**.

## امکانات

- **پنج فرمت ورودی** — تک IP، CIDR (`1.0.0.0/24`)، رنج (`1.0.0.1-1.0.0.50`)، دامنه (`github.com`)، URL کامل (`https://api.github.com`)
- **سه روش بررسی:**
  - `icmp` — پینگ کلاسیک (سریع، پیش‌فرض)
  - `tcp` — اتصال TCP روی پورت ۴۴۳ (وقتی ICMP بسته باشه)
  - `http` — درخواست HTTPS `HEAD` (مناسب هاست‌های پشت CDN)
- **چندسکویی** — ویندوز، لینوکس، مک
- **اندازه‌گیری latency** برای هر هاست زنده
- **اسکن موازی** (۱۰۰ thread پیش‌فرض، قابل تنظیم)
- **سه فرمت خروجی** — TXT، JSON، CSV
- **دو حالت اجرا** — منوی تعاملی یا CLI با flag
- **حفظ ورودی اصلی در خروجی** — اگه `github.com` بدی، خروجی هم `github.com` می‌مونه (نه فقط IP)

## نصب

### از سورس (نیاز به Python)

```bash
git clone https://github.com/penhandev/IP-Scanner.git
cd IP-Scanner
pip install -r requirements.txt
python scanner.py
```

نیاز به **Python نسخه ۳.۱۰ یا بالاتر**.

### دانلود نسخه آماده (ویندوز، بدون Python)

از بخش [Releases](https://github.com/penhandev/IP-Scanner/releases) آخرین فایل `.exe` رو دانلود کن و مستقیم اجرا کن.

## نحوه استفاده

### حالت تعاملی

```bash
python scanner.py
```

ابزار همه فایل‌های `.txt` توی پوشه فعلی رو لیست می‌کنه و یکی رو انتخاب می‌کنی.

### حالت دستوری (CLI)

```bash
python scanner.py -f targets.txt                   # ICMP ping
python scanner.py -f targets.txt -m tcp            # اتصال TCP پورت 443
python scanner.py -f targets.txt -m http           # درخواست HTTPS HEAD
python scanner.py -f targets.txt -o txt json csv   # خروجی چندفرمته
python scanner.py -f targets.txt -w 200            # 200 thread موازی
python scanner.py --help                           # راهنمای کامل
```

### فرمت فایل ورودی

```text
# خطوطی که با # شروع می‌شن کامنت محسوب می‌شن

# تک IP
8.8.8.8
1.1.1.1

# CIDR
192.168.1.0/24

# رنج IPv4
10.0.0.1-10.0.0.50

# دامنه
github.com
www.cloudflare.com

# URL
https://api.github.com/v3
http://example.com/path
```

## خروجی

برای فایل ورودی `targets.txt`، این فایل‌ها ساخته می‌شن:

- `results_targets.txt` — لیست هاست‌های زنده، یکی در هر خط
- `results_targets.json` — اطلاعات کامل با latency، خطا، روش بررسی
- `results_targets.csv` — همون اطلاعات، مناسب اکسل

فقط فرمت‌هایی که با `-o` انتخاب می‌کنی ساخته می‌شن. پیش‌فرض فقط `txt` هست.

## ساختار پروژه

```text
IP-Scanner/
├── scanner.py              # نقطه شروع (منو + argparse)
├── ipscanner/
│   ├── __init__.py
│   ├── parser.py           # پارس ورودی (CIDR / رنج / URL / دامنه)
│   ├── checker.py          # بررسی ICMP / TCP / HTTP
│   ├── exporter.py         # خروجی TXT / JSON / CSV
│   └── ui.py               # helpers برای Rich
├── targets.txt             # ورودی نمونه (همچنین: akami.txt, amazon.txt, cloudflare.txt, fastly.txt)
├── .github/workflows/      # خودکارسازی build و release
├── requirements.txt
├── .gitignore
└── LICENSE
```

## نقشه راه

- [ ] backend ناهمگام (`asyncio` + `aiohttp`) برای سرعت ۱۰ برابری روی لیست‌های بزرگ
- [ ] جستجوی Reverse DNS روی IPهای زنده
- [ ] تگ‌گذاری GeoIP / ASN (تشخیص کشور و سازمان)
- [ ] قابلیت ادامه بعد از قطع شدن (resume)
- [ ] فایل پیکربندی (`.toml`) برای flag های پیش‌فرض

## مشارکت

Pull request ها استقبال می‌شن. برای فیچرهای بزرگ، اول یه issue باز کن تا بحث کنیم.

## سلب مسئولیت

این ابزار فقط **بررسی اتصال خواندنی (read-only)** انجام می‌ده. فقط روی هاست‌هایی استفاده کن که خودت مالکش هستی یا اجازه تست داری.

## لایسنس

MIT — فایل [LICENSE](LICENSE) رو ببین.

</div>

---

## نصب روی Termux (Android)

### ۱. پکیج‌های پایه را نصب کن

```bash
pkg update && pkg upgrade -y
pkg install python git -y
```

### ۲. ابزار را دریافت کن

```bash
git clone https://github.com/penhandev/IP-Scanner.git
cd IP-Scanner
pip install -r requirements.txt
```

### ۳. اجرا کن

```bash
# حالت تعاملی
python scanner.py

# حالت دستوری
python scanner.py -f targets.txt -m tcp
```

### ⚠ محدودیت ICMP روی Android

روی Android بدون root، ICMP ping کار نمی‌کند. به جای آن از TCP یا HTTP استفاده کن:

| روش | دستور | مناسب برای |
|-----|-------|-----------|
| TCP | `-m tcp` | بیشتر IP های معمولی |
| HTTP | `-m http` | سایت‌ها و CDN ها |

اگر گوشی root دارد، می‌توانی از حالت ICMP هم استفاده کنی.

### نکته Termux: فایل‌های txt کجا باشن؟

وقتی `scanner.py` اجرا می‌شه، دنبال فایل‌های `.txt` توی همون پوشه می‌گرده. پس فایل targets رو کنار `scanner.py` بذار یا مستقیم با `-f` مسیرش رو بده:

```bash
python scanner.py -f /sdcard/Download/targets.txt -m tcp
```
