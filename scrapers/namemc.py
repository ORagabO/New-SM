"""namemc.com - Cloudflare-protected -> browser."""
import re
import logging

from .base import BrowserScraper, normalize

log = logging.getLogger("scraper")

# ---- plug-in points -------------------------------------------------------
BASE = "https://namemc.com/minecraft-skins"
WAIT_SELECTOR = "a[href^='/skin/']"
ID_RE = re.compile(r"/skin/([0-9a-fA-F]+)")
# Reads each card: link, name (.card-header), image (data-src), a corner stat.
CARD_JS = """els => els.map(card => {
  const a = card.querySelector("a[href^='/skin/']");
  const img = card.querySelector('img');
  const q = (s) => { const e = card.querySelector(s); return e ? e.textContent.trim() : ''; };
  return {
    href: a ? a.getAttribute('href') : '',
    name: q('.card-header'),
    src: img ? (img.getAttribute('data-src') || img.currentSrc || img.getAttribute('src') || '') : '',
    stat: q('.position-absolute.bottom-0.end-0'),
  };
})"""
# ---------------------------------------------------------------------------


class NameMCScraper(BrowserScraper):
    source = "namemc"
    wait_selector = WAIT_SELECTOR

    def __init__(self, pages: int):
        super().__init__(pages)
        self._seen = set()

    def page_url(self, n: int) -> str:
        return BASE if n == 1 else f"{BASE}?page={n}"

    def extract(self, page) -> list[dict]:
        cards = page.eval_on_selector_all("div.card", CARD_JS)
        out = []
        for c in cards:
            m = ID_RE.search(c.get("href") or "")
            if not m:
                continue
            sid = m.group(1)
            if sid in self._seen:
                continue
            self._seen.add(sid)
            img = c.get("src") or (
                f"https://s.namemc.com/3d/skin/body.png?id={sid}&model=slim&width=256&height=256")
            out.append(normalize(
                source=self.source,
                name=c.get("name") or None,
                image_url=img,
                download_url=f"https://namemc.com/skin/{sid}",
                downloads=c.get("stat") or None,
                id=sid,
            ))
        return out
