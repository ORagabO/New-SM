# Skins Scraper + API

Modular scraper for 4 skin sites (laby.net, The Skindex, NameMC,
minecraftskins.net) with a generic template for adding more, a FastAPI
read endpoint, and twice-a-week automation.

## Structure

```
skins-scraper/
├── config.py                 # settings, anti-detection knobs, site toggles, generic sites
├── scraper.py                # orchestrator: runs all scrapers -> scraped_data.json
├── api.py                    # FastAPI: GET /api/data
├── requirements.txt
├── scraped_data.json         # generated output
├── scrapers/
│   ├── __init__.py
│   ├── base.py               # HttpScraper (curl_cffi) + BrowserScraper (Playwright)
│   ├── laby.py               # JSON API      (HTTP)
│   ├── mcnet.py              # minecraftskins.net (HTTP + BeautifulSoup)
│   ├── skindex.py            # minecraftskins.com (browser, Cloudflare JS)
│   ├── namemc.py             # namemc.com         (browser, Cloudflare)
│   └── template_site.py      # generic CSS-selector scraper for new sites
└── .github/workflows/
    └── scrape.yml            # scheduled Actions workflow (Tue & Fri 02:00 UTC)
```

## Setup

```bash
cd skins-scraper
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium                  # browser for Skindex/NameMC
```

## Run the scraper

```bash
python scraper.py            # writes scraped_data.json
```

Tune what runs and how deep in `config.py` → `SITES`. To add a new site with
no new code, copy an entry in `config.GENERIC_SITES` and fill in the CSS
selectors.

## Run the API

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

- `GET http://localhost:8000/api/data` — full payload
- `GET /api/data?source=laby&limit=100&offset=0` — filtered + paginated
- `GET /api/health` — status
- Interactive docs at `http://localhost:8000/docs`

## Automation — twice a week (Tuesday & Friday, 02:00)

### Option A — Linux cron

`crontab -e`, then add (adjust the absolute paths):

```cron
0 2 * * 2,5 cd /path/to/skins-scraper && /path/to/skins-scraper/.venv/bin/python scraper.py >> scrape.log 2>&1
```

`0 2 * * 2,5` = minute 0, hour 2, any day of month, any month, on weekday
2 (Tue) and 5 (Fri). Browser sources need a display; on a headless server run
it under Xvfb:

```cron
0 2 * * 2,5 cd /path/to/skins-scraper && xvfb-run -a /path/to/skins-scraper/.venv/bin/python scraper.py >> scrape.log 2>&1
```

### Option B — GitHub Actions

`.github/workflows/scrape.yml` is included and runs on the same schedule
(`cron: "0 2 * * 2,5"`), installs everything (including Xvfb), runs the
scraper, and commits `scraped_data.json`. Trigger it manually anytime from the
repo's **Actions** tab. Note: cron is **UTC** — shift the hour for your timezone.

## Anti-detection — honest notes

The scraper already uses the strongest in-process techniques:

- **curl_cffi** with a real Chrome TLS/JA3 fingerprint for HTTP sources (laby,
  mcnet) — defeats fingerprint-based Cloudflare checks that plain `requests` fails.
- **Headful Chromium + stealth patches** (run under Xvfb on servers) for the JS
  challenge sites (Skindex, NameMC) — a real browser executes the challenge.
- Realistic headers, retries with backoff, challenge detection, polite delays.

No in-process trick is 100%. Cloudflare's remaining lever is **IP reputation**:
datacenter IPs (including GitHub Actions runners) can still be challenged even
with a perfect fingerprint. The two reliable fixes:

1. **Run from a residential/mobile IP** (a home machine, a small VPS that isn't
   flagged, or your own box) — Cloudflare challenges these far less.
2. **Route through a residential/mobile proxy**: set `SCRAPER_PROXY`
   (e.g. `export SCRAPER_PROXY="http://user:pass@host:port"`) and every HTTP and
   browser request goes through it. This is the standard way to stay undetected
   at scale.

The design degrades gracefully: if a protected site blocks a given run, that
scraper returns nothing and the others still produce data — the run never crashes.
```
