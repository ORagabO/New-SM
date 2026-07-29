"""
Lightweight REST API over scraped_data.json.

Run:
    uvicorn api:app --reload --host 0.0.0.0 --port 8000

Endpoints:
    GET /api/data      -> full aggregated payload (optionally paged/filtered)
    GET /api/health    -> liveness + basic stats
"""
import json
import os

from fastapi import FastAPI, HTTPException, Query

import config

app = FastAPI(title="Skins Data API", version="1.0.0")


def _load():
    if not os.path.exists(config.OUTPUT_FILE):
        raise HTTPException(status_code=404,
                            detail="scraped_data.json not found. Run the scraper first.")
    try:
        with open(config.OUTPUT_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not read data: {e}")


@app.get("/api/data")
def get_data(
    source: str | None = Query(None, description="Filter by source, e.g. laby"),
    limit: int | None = Query(None, ge=1, le=1000, description="Items per page"),
    offset: int = Query(0, ge=0, description="Items to skip"),
):
    """Return the aggregated scraped data. Without params, returns everything."""
    payload = _load()
    items = payload.get("data", [])

    if source:
        items = [i for i in items if i.get("source") == source]

    total_matched = len(items)
    if limit is not None:
        items = items[offset:offset + limit]
    elif offset:
        items = items[offset:]

    return {
        "generated_at": payload.get("generated_at"),
        "total": payload.get("total"),
        "returned": len(items),
        "matched": total_matched,
        "offset": offset,
        "limit": limit,
        "sources": payload.get("sources", {}),
        "data": items,
    }


@app.get("/api/health")
def health():
    exists = os.path.exists(config.OUTPUT_FILE)
    payload = _load() if exists else {}
    return {
        "status": "ok",
        "data_file_present": exists,
        "total": payload.get("total", 0),
        "generated_at": payload.get("generated_at"),
    }
