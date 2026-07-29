"""minecraftskins.net - server-rendered HTML. HTTP-only (no browser needed)."""
import re
import logging

from bs4 import BeautifulSoup

from .base import HttpScraper, normalize

log = logging.getLogger("scraper")

# ---- plug-in points -------------------------------------------------------
BASE = "https://www.minecraftskins.net"
PAGE_URL = BASE + "/page/{page}"        # page 1 is just BASE
IMG_SELECTOR = "img.skin-image"          # each front-preview image
IMG_RE = re.compile(r"/static/front_preview/([^/.\"]+)\.png", re.I)
# ---------------------------------------------------------------------------


class McnetScraper(HttpScraper):
    source = "mcnet"

    def __init__(self, pages: int):
        super().__init__()
        self.pages = pages

    def run(self) -> list[dict]:
        out, seen = [], set()
        for n in range(1, self.pages + 1):
            url = BASE if n == 1 else PAGE_URL.format(page=n)
            html = self.fetch(url)
            if not html:
                break
            soup = BeautifulSoup(html, "html.parser")
            imgs = soup.select(IMG_SELECTOR)
            if not imgs:
                break
            new = 0
            for img in imgs:
                src = img.get("src") or ""
                m = IMG_RE.search(src)
                if not m:
                    continue
                slug = m.group(1)
                if slug in seen:
                    continue
                seen.add(slug)
                new += 1
                out.append(normalize(
                    source=self.source,
                    name=(img.get("alt") or slug).strip(),
                    image_url=f"{BASE}/static/front_preview/{slug}.png",
                    download_url=f"{BASE}/{slug}/download",
                    downloads=None,
                    id=slug,
                ))
            if new == 0:
                break
        log.info("[mcnet] collected %d", len(out))
        return out
