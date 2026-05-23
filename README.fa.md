# Penhandev IP-Scanner

> **زبان‌ها:** [English](README.md) · **فارسی**

<div dir="rtl">

ابزار سریع و چندسکویی برای بررسی در دسترس بودن **آی‌پی‌ها، CIDR، رنج‌های IP، دامنه‌ها و URL ها**.

## امکانات

- **پنج فرمت ورودی** — تک IP، CIDR (`1.0.0.0/24`)، رنج (`1.0.0.1-1.0.0.50`)، دامنه (`github.com`)، URL کامل (`https://api.github.com`)
- **سه روش بررسی:**
  - `icmp` — پینگ کلاسیک (سریع، پیش‌فرض؛ روی اکثر گوشی‌های Android بدون root هم با ICMP بدون‌مجوز کار می‌کنه)
  - `tcp` — اتصال TCP روی هر پورتی که انتخاب کنی (`-p`، پیش‌فرض `443`؛ برای HTTP معمولی `80` بزن)
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

### راه ساده — فقط اجراش کن

```bash
python scanner.py
```

یه منو باز می‌شه. یه فایل انتخاب کن، یه روش بررسی انتخاب کن، Enter بزن. تمام.

### راه حرفه‌ای — با flag

```bash
python scanner.py -f targets.txt -m tcp -p 80
```

این خط یعنی: «از فایل `targets.txt` استفاده کن، با TCP بررسی کن، پورت ۸۰ رو بزن.»

## همه گزینه‌ها (Flag ها) — به زبان ساده

هرکدوم رو خواستی استفاده کن. لازم نیست همه رو با هم بزنی.

### ۱. هدف‌ها از کجا میان؟ (یکی رو انتخاب کن)

| Flag | کوتاه | یعنی چی |
|---|---|---|
| `--file FILE` | `-f` | «از این فایل متنی هدف‌ها رو بخون.» مثال: `-f cloudflare.txt` |
| `--target ...` | `-t` | «این هدف‌ها رو همین الان بهت می‌گم.» مثال: `-t 1.1.1.1 github.com 8.8.8.8` |
| `--input` | — | «بذار خط به خط دستی تایپ کنم، آخرش یه خط خالی بزنم تمام.» |

اگه هیچ‌کدوم رو نزنی، منوی تعاملی باز می‌شه.

### ۲. هر هدف چجوری بررسی بشه؟

| Flag | کوتاه | یعنی چی |
|---|---|---|
| `-m icmp` | — | یه **پینگ معمولی** بفرست. سریع‌ترین. روی اکثر گوشی‌های Android بدون root هم کار می‌کنه. |
| `-m tcp` | — | روی یه **پورت TCP اتصال** بزن. تقریباً همه‌جا کار می‌کنه. |
| `-m http` | — | یه **درخواست HTTPS HEAD کوچیک** بفرست. مناسب سایت‌های پشت CDN. |

### ۳. بقیه گزینه‌ها

| Flag | کوتاه | یعنی چی |
|---|---|---|
| `--port PORT` | `-p` | فقط با `-m tcp` معنی داره. کدوم پورت رو بزنی. پیش‌فرض `443` (HTTPS). برای HTTP معمولی `80` بذار. مثال: `-p 80` |
| `--workers N` | `-w` | چندتا بررسی هم‌زمان انجام بشه. پیش‌فرض `100`. بیشتر = سریع‌تر ولی سنگین‌تر. مثال: `-w 200` |
| `--output FORMATS` | `-o` | چه نوع خروجی ذخیره بشه. از بین `txt`، `json`، `csv` انتخاب کن. پیش‌فرض `txt`. مثال: `-o txt json csv` |
| `--no-resolve` | — | «دامنه‌ها رو به IP تبدیل نکن.» سریع‌تره ولی IP توی گزارش نمی‌بینی. |
| `--verbose` | `-v` | موقع اجرا اطلاعات بیشتر چاپ کن. وقتی یه چیزی خراب شده مفیده. |
| `--version` | — | فقط نسخه رو چاپ کن و خارج شو. |
| `--help` | `-h` | کل این لیست رو توی ترمینال نشون بده. |

### دستورهای سریع آماده

```bash
# ۱. ساده‌ترین حالت — همه IP های فایل رو پینگ کن
python scanner.py -f targets.txt

# ۲. مناسب Android — TCP روی پورت ۸۰، ذخیره به همه فرمت‌ها
python scanner.py -f cloudflare.txt -m tcp -p 80 -o txt json csv

# ۳. سه چیز سریع همین الان
python scanner.py -t 1.1.1.1 8.8.8.8 github.com -m tcp

# ۴. هدف‌ها رو دستی تایپ کن
python scanner.py --input -m http

# ۵. اسکن بزرگ، سریع‌تر — ۳۰۰ worker
python scanner.py -f big_list.txt -w 300
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

### ⚠ توضیح ICMP روی Android

روی اکثر گوشی‌های Android جدید، حتی **بدون root** هم ICMP کار می‌کنه (به صورت «ICMP بدون‌مجوز» از طریق SOCK_DGRAM). موقع اجرا اگه پشتیبانی بشه، scanner خودش پیغام «✓ Unprivileged ICMP available» نشون می‌ده و ادامه می‌ده.

اگه کرنل گوشیت این رو پشتیبانی نکنه (پیغام مربوط به root میاد)، از TCP یا HTTP استفاده کن:

| روش | دستور | مناسب برای |
|-----|-------|-----------|
| TCP | `-m tcp` (پورت پیش‌فرض ۴۴۳، با `-p 80` می‌تونی عوض کنی) | بیشتر IP های معمولی |
| HTTP | `-m http` | سایت‌ها و CDN ها |

اگر گوشی root داره، scanner می‌تونه با اجازه‌ت دوباره با `su` اجرا بشه و ICMP کامل کار کنه.

### نکته Termux: فایل‌های txt کجا باشن؟

وقتی `scanner.py` اجرا می‌شه، دنبال فایل‌های `.txt` توی همون پوشه می‌گرده. پس فایل targets رو کنار `scanner.py` بذار یا مستقیم با `-f` مسیرش رو بده:

```bash
python scanner.py -f /sdcard/Download/targets.txt -m tcp
```
