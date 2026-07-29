"""
Generic, config-driven scraper for onboarding a NEW site with zero new code.

Add an entry to config.GENERIC_SITES with the site's URL pattern and the CSS
selectors for each field. This class turns that config into a working scraper
using requests-style fetching (curl_cffi) + BeautifulSoup. If a site is
JavaScript-heavy or Cloudflare-challenged, model it on skindex.py/namemc.py
(BrowserScraper) instead.
"""
import logging

from bs4 import BeautifulSoup

from .base import HttpScraper, normalize

log = logging.getLogger("scraper")


class GenericScraper(HttpScraper):
    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        self.source = cfg["source"]

    def _text(self, node, selector):
        if not selector:
            return None
        el = node.select_one(selector)
        return el.get_text(strip=True) if el else None

    def _attr(self, node, selector, attr):
        if not selector:
            return None
        el = node.select_one(selector)
        return el.get(attr) if el else None

    def run(self) -> list[dict]:
        cfg = self.cfg
        out = []
        for n in range(1, cfg.get("pages", 1) + 1):
            html = self.fetch(cfg["url"].format(page=n))
            if not html:
                break
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select(cfg["item_selector"])
            if not cards:
                break
            for card in cards:
                out.append(normalize(
                    source=self.source,
                    name=self._text(card, cfg.get("name_selector")),
                    image_url=self._attr(card, cfg.get("image_selector"),
                                         cfg.get("image_attr", "src")),
                    download_url=self._attr(card, cfg.get("link_selector"),
                                            cfg.get("link_attr", "href")),
                    downloads=self._text(card, cfg.get("downloads_selector")),
                    id=self._attr(card, cfg.get("link_selector"),
                                  cfg.get("link_attr", "href")),
                ))
        log.info("[%s] collected %d", self.source, len(out))
        return out
