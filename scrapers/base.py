"""
Shared scraper infrastructure.

Two base classes:
  * HttpScraper    - for JSON APIs and server-rendered HTML. Uses curl_cffi with
                     browser fingerprint impersonation (defeats TLS-fingerprint
                     Cloudflare checks) + retries + challenge detection.
  * BrowserScraper - for JavaScript / Cloudflare-managed-challenge sites. Drives
                     a headful Chromium (stealth-patched) that executes the
                     challenge JS and reuses the cleared session across pages.

Every scraper returns a list of dicts in one common shape:
    {source, name, image_url, download_url, downloads, id}
"""
from __future__ import annotations

import time
import logging
from typing import Iterable

import config

log = logging.getLogger("scraper")

# Markers that mean Cloudflare served a challenge instead of the real page.
CHALLENGE_MARKERS = (
    "Just a moment",
    "Enable JavaScript and cookies to continue",
    "cf-mitigated",
    "challenge-platform",
    "cf_chl_opt",
)

HEADERS = {
    "User-Agent": config.USER_AGENT,
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
}

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
window.chrome = { runtime: {} };
"""


def looks_challenged(status: int, body: str) -> bool:
    if status in (403, 429, 503):
        return True
    head = (body or "")[:4000]
    return any(m in head for m in CHALLENGE_MARKERS)


def normalize(source, name=None, image_url=None, download_url=None,
              downloads=None, id=None) -> dict:
    """Force every scraper's output into the same schema."""
    return {
        "source": source,
        "name": name,
        "image_url": image_url,
        "download_url": download_url,
        "downloads": downloads,
        "id": str(id) if id is not None else None,
    }


class BaseScraper:
    source = "base"

    def run(self) -> list[dict]:
        raise NotImplementedError


class HttpScraper(BaseScraper):
    """For JSON APIs and static HTML pages."""

    def __init__(self):
        from curl_cffi import requests as cffi
        proxies = {"http": config.PROXY, "https": config.PROXY} if config.PROXY else None
        self.session = cffi.Session(
            impersonate=config.IMPERSONATE,
            headers=HEADERS,
            timeout=config.REQUEST_TIMEOUT,
            proxies=proxies,
        )

    def fetch(self, url: str) -> str | None:
        """GET with retries + Cloudflare-challenge detection. Returns text or None."""
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                r = self.session.get(url)
                if r.status_code == 200 and not looks_challenged(r.status_code, r.text):
                    return r.text
                reason = ("challenge" if looks_challenged(r.status_code, r.text)
                          else f"status {r.status_code}")
                log.warning("[%s] %s (attempt %d/%d)", self.source, reason,
                            attempt, config.MAX_RETRIES)
            except Exception as e:
                log.warning("[%s] request error: %s (attempt %d/%d)", self.source, e,
                            attempt, config.MAX_RETRIES)
            time.sleep(config.RETRY_BACKOFF * attempt)
        return None

    def fetch_json(self, url: str):
        import json
        text = self.fetch(url)
        if text is None:
            return None
        try:
            return json.loads(text)
        except Exception as e:
            log.warning("[%s] bad JSON: %s", self.source, e)
            return None


class BrowserScraper(BaseScraper):
    """
    For Cloudflare JS-challenge sites. Subclasses implement:
        page_url(n)  -> str
        extract(page) -> list[dict]   (normalized entries)
    and set `wait_selector` (a CSS selector that only appears once the
    challenge has cleared and real content is present).
    """
    wait_selector = "body"

    def __init__(self, pages: int):
        self.pages = pages

    # ---- subclass hooks ----
    def page_url(self, n: int) -> str:
        raise NotImplementedError

    def extract(self, page) -> list[dict]:
        raise NotImplementedError

    # ---- driver ----
    def run(self) -> list[dict]:
        from playwright.sync_api import sync_playwright
        results: list[dict] = []
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox", "--disable-dev-shm-usage", "--start-maximized",
        ]
        proxy = {"server": config.PROXY} if config.PROXY else None
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not config.HEADFUL,
                                        args=launch_args, proxy=proxy)
            ctx = browser.new_context(user_agent=config.USER_AGENT,
                                      viewport={"width": 1366, "height": 900},
                                      locale="en-US")
            ctx.add_init_script(STEALTH_JS)
            page = ctx.new_page()
            for n in range(1, self.pages + 1):
                url = self.page_url(n)
                log.info("[%s] page %d/%d", self.source, n, self.pages)
                try:
                    page.goto(url, wait_until="domcontentloaded",
                              timeout=config.REQUEST_TIMEOUT * 1000)
                except Exception as e:
                    log.warning("[%s] nav error: %s", self.source, e)
                    break
                if not self._wait_clear(page):
                    log.warning("[%s] challenge not cleared; stopping source.", self.source)
                    break
                batch = self.extract(page)
                if not batch:
                    break
                results.extend(batch)
                time.sleep(config.PAGE_DELAY)
            browser.close()
        return results

    def _wait_clear(self, page) -> bool:
        deadline = time.time() + config.CHALLENGE_WAIT
        while time.time() < deadline:
            try:
                if page.query_selector(self.wait_selector):
                    return True
            except Exception:
                pass
            time.sleep(1)
        return bool(page.query_selector(self.wait_selector))
