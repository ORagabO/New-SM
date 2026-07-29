"""laby.net - JSON search API. Fast, paginated, HTTP-only."""
import logging

from .base import HttpScraper, normalize
import config

log = logging.getLogger("scraper")

# ---- plug-in points -------------------------------------------------------
API = ("https://laby.net/api/v3/search/textures/skin"
       "?order=most_used&size={size}&offset={offset}")
PAGE_SIZE = 36
RENDER = "https://laby.net/api/v3/render/skin/{hash}.png?height=500&width=500"
TEXTURE = "https://textures.minecraft.net/texture/{hash}"
# ---------------------------------------------------------------------------


def _first(d, keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", []):
            return v
    return None


class LabyScraper(HttpScraper):
    source = "laby"

    def __init__(self, pages: int):
        super().__init__()
        self.pages = pages

    def run(self) -> list[dict]:
        out, seen = [], set()
        for i in range(self.pages):
            data = self.fetch_json(API.format(size=PAGE_SIZE, offset=i * PAGE_SIZE))
            if not data:
                break
            items = data if isinstance(data, list) else _first(
                data, ["results", "data", "textures", "skins", "hits"]) or []
            if not items:
                break
            for sk in items:
                h = _first(sk, ["hash", "image_hash", "id", "texture_id"])
                if not h or h in seen:
                    continue
                seen.add(h)
                out.append(normalize(
                    source=self.source,
                    name=_first(sk, ["name", "title", "display_name"]),
                    image_url=RENDER.format(hash=h),
                    download_url=TEXTURE.format(hash=h),
                    downloads=_first(sk, ["useCount", "usages", "used", "users", "count"]),
                    id=h,
                ))
        log.info("[laby] collected %d", len(out))
        return out
