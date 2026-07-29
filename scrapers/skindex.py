"""minecraftskins.com (The Skindex) - Cloudflare JS challenge -> browser."""
import re
import logging

from .base import BrowserScraper, normalize

log = logging.getLogger("scraper")

# ---- plug-in points -------------------------------------------------------
BASE = "https://www.minecraftskins.com"
LISTING = BASE + "/latest/{page}/"
WAIT_SELECTOR = "a[href*='/skin/']"      # appears only after challenge clears
HREF_RE = re.compile(r"/skin/(\d+)/([^/?#\"']+)")
IMG_RE = re.compile(r"/uploads/(?:preview-)?skins/[^\s\"']*?-(\d+)\.png")
# ---------------------------------------------------------------------------


class SkindexScraper(BrowserScraper):
    source = "skindex"
    wait_selector = WAIT_SELECTOR

    def page_url(self, n: int) -> str:
        return LISTING.format(page=n)

    def extract(self, page) -> list[dict]:
        hrefs = page.eval_on_selector_all(
            "a[href*='/skin/']", "els => els.map(e => e.getAttribute('href'))")
        srcs = page.eval_on_selector_all(
            "img", "els => els.map(e => e.currentSrc || e.getAttribute('src') "
                   "|| e.getAttribute('data-src') || '')")
        ids = {}
        for h in hrefs:
            m = HREF_RE.search(h or "")
            if m:
                ids.setdefault(m.group(1), m.group(2))
        imgs = {}
        for s in srcs:
            s = s or ""
            m = IMG_RE.search(s)
            if m:
                clean = s.split("?")[0]
                imgs[m.group(1)] = clean if clean.startswith("http") else BASE + clean
        return [normalize(
            source=self.source,
            name=slug.replace("-", " ").strip(),
            image_url=imgs.get(sid) or f"{BASE}/skin/download/{sid}",
            download_url=f"{BASE}/skin/download/{sid}",
            downloads=None,
            id=sid,
        ) for sid, slug in ids.items()]
