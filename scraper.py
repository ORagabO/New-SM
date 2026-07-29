"""
Orchestrator. Runs every enabled scraper, aggregates the results into one
well-structured dict, and writes scraped_data.json.

Each scraper runs inside try/except so one failing site (e.g. Cloudflare block)
never crashes the whole run.

    python scraper.py
"""
import json
import time
import logging
from datetime import datetime, timezone

import config
from scrapers import (LabyScraper, SkindexScraper, NameMCScraper,
                      McnetScraper, GenericScraper)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scraper")


def build_jobs():
    """Instantiate the scrapers that are enabled in config."""
    jobs = []
    s = config.SITES
    if s["laby"]["enabled"]:
        jobs.append(LabyScraper(s["laby"]["pages"]))
    if s["skindex"]["enabled"]:
        jobs.append(SkindexScraper(s["skindex"]["pages"]))
    if s["namemc"]["enabled"]:
        jobs.append(NameMCScraper(s["namemc"]["pages"]))
    if s["mcnet"]["enabled"]:
        jobs.append(McnetScraper(s["mcnet"]["pages"]))
    for cfg in config.GENERIC_SITES:
        jobs.append(GenericScraper(cfg))
    return jobs


def dedupe(items):
    seen, out = set(), []
    for it in items:
        key = (it.get("source"), it.get("id"))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def main():
    started = time.time()
    all_items, per_source = [], {}

    for job in build_jobs():
        name = job.source
        log.info("=== running %s ===", name)
        try:
            items = job.run()
        except Exception as e:               # one site failing must not crash the run
            log.error("[%s] FAILED, skipping: %s", name, e)
            items = []
        per_source[name] = len(items)
        all_items.extend(items)

    all_items = dedupe(all_items)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "duration_seconds": round(time.time() - started, 1),
        "total": len(all_items),
        "sources": per_source,
        "data": all_items,
    }

    with open(config.OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    log.info("Done. %d items from %s -> %s",
             len(all_items), per_source, config.OUTPUT_FILE)


if __name__ == "__main__":
    main()
