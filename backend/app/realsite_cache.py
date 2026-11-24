"""Loads and serves the real-website demo cache.

This is a separate, much simpler concern from the ML model: it just reads
pre-extracted clause text for a small set of real sites, produced offline
by backend/scripts/build_realsite_cache.py. No prediction happens here -
the extension classifies these clauses live via /predict-batch using
whatever model is currently trained, so results always reflect the current
model rather than a stale pre-baked snapshot.

Storage layout (easy to browse and extend by hand if needed):

    backend/data/realsite_cache/<domain>/meta.json     {"site_name", "fetched_at"}
    backend/data/realsite_cache/<domain>/terms.json    {"source_url", "clauses": [...]}
    backend/data/realsite_cache/<domain>/privacy.json  {"source_url", "clauses": [...]}
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
CACHE_DIR = BACKEND_DIR / "data" / "realsite_cache"

PAGE_TYPES = ("terms", "privacy")


def _normalize_domain(domain: str) -> str:
    domain = domain.lower().strip()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


class RealsiteCache:
    """Reads the cache folder fresh on every call.

    The cache is small (a handful of sites, each a few KB of JSON) and only
    changes when a teacher/student re-runs build_realsite_cache.py, so there
    is no need for in-memory caching or a restart to pick up new sites.
    """

    def get(self, domain: str) -> Optional[dict]:
        site_dir = CACHE_DIR / _normalize_domain(domain)
        meta_path = site_dir / "meta.json"
        if not site_dir.is_dir() or not meta_path.exists():
            return None

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        pages: Dict[str, dict] = {}
        for page_type in PAGE_TYPES:
            page_path = site_dir / f"{page_type}.json"
            if not page_path.exists():
                continue
            try:
                pages[page_type] = json.loads(page_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

        if not pages:
            return None

        return {
            "site_name": meta.get("site_name", _normalize_domain(domain)),
            "fetched_at": meta.get("fetched_at", ""),
            "pages": pages,
        }

    def list_domains(self) -> Dict[str, str]:
        if not CACHE_DIR.is_dir():
            return {}

        domains: Dict[str, str] = {}
        for site_dir in sorted(CACHE_DIR.iterdir()):
            if not site_dir.is_dir():
                continue
            meta_path = site_dir / "meta.json"
            if not meta_path.exists():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            domains[site_dir.name] = meta.get("site_name", site_dir.name)
        return domains


realsite_cache = RealsiteCache()
