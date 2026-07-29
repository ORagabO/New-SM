"""
Central configuration.

Everything you'll routinely tweak lives here: which sites run, how deep,
timeouts/retries, the anti-detection knobs, and the placeholder "generic"
sites where you plug in real CSS selectors later.
"""
import os

# ----------------------------- output --------------------------------------
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "scraped_data.json")

# ----------------------------- HTTP / anti-detection -----------------------
REQUEST_TIMEOUT = 60           # seconds per request
MAX_RETRIES = 4                # attempts per URL before giving up
RETRY_BACKOFF = 2              # seconds; multiplied by attempt number
PAGE_DELAY = 1.5               # polite delay between pages (seconds)

# curl_cffi impersonates a real browser's TLS/JA3 fingerprint. This is what
# gets HTTP sources past fingerprint-based Cloudflare checks that a plain
# `requests` call fails. Options: "chrome", "chrome124", "safari", "edge"...
IMPERSONATE = "chrome"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Optional proxy for the *reliable* anti-detection path (residential/mobile
# IPs). Datacenter IPs (e.g. CI runners) are the main reason Cloudflare still
# challenges even with a perfect fingerprint. Set SCRAPER_PROXY to something
# like "http://user:pass@host:port" to route all traffic through it.
PROXY = os.getenv("SCRAPER_PROXY")

# Browser sources must run headful (under a virtual display on servers) to
# clear Cloudflare's JavaScript challenge. See README for the xvfb command.
HEADFUL = os.getenv("HEADFUL", "1") == "1"
CHALLENGE_WAIT = 30            # seconds to let a JS challenge resolve

# ----------------------------- real skin sites -----------------------------
# Toggle sites and set how deep to scrape. Endpoints/selectors live inside
# each scraper module (scrapers/<name>.py) at the top, clearly marked.
SITES = {
    "laby":    {"enabled": True,  "pages": 40},   # JSON API   (~36/page)
    "skindex": {"enabled": True,  "pages": 20},   # browser    (~48/page)
    "namemc":  {"enabled": True,  "pages": 20},   # browser
    "mcnet":   {"enabled": True,  "pages": 25},   # HTML       (~12/page)
}

# ----------------------------- generic template sites ----------------------
# Placeholder sites scraped with requests + BeautifulSoup. Copy an entry and
# fill in the real CSS selectors to onboard a new site with zero new code.
# `attr` picks which attribute to read for image/link (usually src / href).
GENERIC_SITES = [
    {
        "source": "site1",
        "url": "https://site1.com/skins?page={page}",   # {page} is 1..pages
        "pages": 3,
        "item_selector": "div.card",          # each result card
        "name_selector": "h3.title",          # text -> name
        "image_selector": "img.thumb",        # attr -> image_url
        "image_attr": "src",
        "link_selector": "a.download",        # attr -> download_url
        "link_attr": "href",
        "downloads_selector": "span.downloads",  # optional; text -> downloads
    },
    # {
    #     "source": "site2",
    #     "url": "https://site2.com/list/{page}/",
    #     "pages": 5,
    #     "item_selector": "...",
    #     ...
    # },
]
