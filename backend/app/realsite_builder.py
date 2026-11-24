"""Shared, modular logic for building the real-site demo cache.

Used by BOTH:
  - backend/scripts/build_realsite_cache.py (command-line, for bulk/CI use)
  - the POST /realsite-cache/build API endpoint (for the novice-friendly
    admin HTML form at demo/admin-add-site.html)

so there is exactly one implementation of "render a page with a real
browser and extract clause text", not two copies that could drift apart.

This module does NOT run any predictions - it only stores raw clause text.
Classification always happens live, when a student clicks "Scan" in the
extension, using whatever model is currently trained.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
SOURCES_DIR = BACKEND_DIR / "scripts" / "realsite_sources"
CACHE_DIR = BACKEND_DIR / "data" / "realsite_cache"

MIN_CLAUSE_LENGTH = 40
MAX_CLAUSE_LENGTH = 2000
MAX_CLAUSES_PER_PAGE = 100


class PlaywrightUnavailableError(RuntimeError):
    """Raised when playwright/chromium isn't installed in this environment."""


def normalize_domain(domain: str) -> str:
    domain = domain.lower().strip()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def load_site_configs() -> Dict[str, dict]:
    """Reads every *.json file under backend/scripts/realsite_sources/."""
    configs: Dict[str, dict] = {}
    if not SOURCES_DIR.exists():
        return configs

    for path in sorted(SOURCES_DIR.glob("*.json")):
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        domain = normalize_domain(config.get("domain", ""))
        if not domain or not config.get("pages"):
            continue
        configs[domain] = config
    return configs


def write_site_config(domain: str, site_name: str, pages: Dict[str, str]) -> Path:
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    path = SOURCES_DIR / f"{domain}.json"
    path.write_text(
        json.dumps({"domain": domain, "site_name": site_name, "pages": pages}, indent=2),
        encoding="utf-8",
    )
    return path


def _extract_clauses(page) -> list[str]:
    texts = page.evaluate(
        """
        () => {
          const clone = document.body.cloneNode(true);
          clone.querySelectorAll('nav, header, footer, script, style, noscript, aside, [role="navigation"]')
            .forEach((el) => el.remove());
          return Array.from(clone.querySelectorAll('p, li')).map((el) => el.textContent || '');
        }
        """
    )
    seen = set()
    clauses = []
    for text in texts:
        cleaned = " ".join(text.split())
        if len(cleaned) < MIN_CLAUSE_LENGTH or len(cleaned) > MAX_CLAUSE_LENGTH:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        clauses.append(cleaned)
        if len(clauses) >= MAX_CLAUSES_PER_PAGE:
            break
    return clauses


def _get_sync_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise PlaywrightUnavailableError(
            "playwright is not installed in this environment. "
            "Run: pip install playwright && playwright install chromium"
        ) from exc
    return sync_playwright


def build_one_site(domain: str, config: dict, log=print) -> dict:
    """Renders every configured page for one site and writes the cache
    folder. Returns a small summary dict (also useful as an API response).
    """
    sync_playwright = _get_sync_playwright()
    domain = normalize_domain(domain)
    site_dir = CACHE_DIR / domain
    site_dir.mkdir(parents=True, exist_ok=True)

    pages_result: Dict[str, dict] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for page_type, url in config["pages"].items():
            start = time.perf_counter()
            log(f"Rendering {page_type}: {url}")
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                clauses = _extract_clauses(page)
                elapsed = time.perf_counter() - start
                log(f"  -> {len(clauses)} candidate clauses in {elapsed:.1f}s")

                (site_dir / f"{page_type}.json").write_text(
                    json.dumps({"source_url": url, "clauses": clauses}, indent=2),
                    encoding="utf-8",
                )
                pages_result[page_type] = {
                    "source_url": url,
                    "clause_count": len(clauses),
                    "seconds": round(elapsed, 1),
                }
            except Exception as exc:  # noqa: BLE001
                log(f"  -> FAILED: {exc}")
                pages_result[page_type] = {"source_url": url, "error": str(exc)}
        page.close()
        browser.close()

    successful_pages = {k: v for k, v in pages_result.items() if "error" not in v}
    if successful_pages:
        (site_dir / "meta.json").write_text(
            json.dumps(
                {
                    "site_name": config["site_name"],
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    return {
        "domain": domain,
        "site_name": config["site_name"],
        "pages": pages_result,
        "cached": bool(successful_pages),
    }


def add_and_build_site(
    domain: str,
    site_name: str,
    terms_url: Optional[str],
    privacy_url: Optional[str],
    log=print,
) -> dict:
    """Scaffolds a new realsite_sources/<domain>.json config AND builds its
    cache immediately. Used by both --add on the CLI and the admin HTML
    form's API endpoint - the single modular entry point for "add a new
    site" as a student or teacher.
    """
    domain = normalize_domain(domain)
    pages = {}
    if terms_url:
        pages["terms"] = terms_url
    if privacy_url:
        pages["privacy"] = privacy_url

    if not pages:
        raise ValueError("At least one of terms_url/privacy_url is required.")

    write_site_config(domain, site_name, pages)
    config = {"site_name": site_name, "pages": pages}
    return build_one_site(domain, config, log=log)
