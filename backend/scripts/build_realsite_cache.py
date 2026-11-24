"""CLI wrapper for building the real-website demo cache.

The actual logic lives in backend/app/realsite_builder.py (shared with the
POST /realsite-cache/build API endpoint used by the admin HTML form), so
there is exactly one implementation to maintain.

Usage:
    python backend/scripts/build_realsite_cache.py                # build all configured sites
    python backend/scripts/build_realsite_cache.py --only github.com
    python backend/scripts/build_realsite_cache.py --add example.com \\
        --name "Example Inc." \\
        --terms-url "https://example.com/terms" \\
        --privacy-url "https://example.com/privacy"

Requires (dev-only, not needed to run the API or extension at runtime):
    pip install playwright
    playwright install chromium
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.realsite_builder import (  # noqa: E402
    CACHE_DIR,
    PlaywrightUnavailableError,
    SOURCES_DIR,
    add_and_build_site,
    build_one_site,
    load_site_configs,
    normalize_domain,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", metavar="DOMAIN", help="Build just this one already-configured domain.")
    parser.add_argument("--add", metavar="DOMAIN", help="Scaffold a new site config and build it immediately.")
    parser.add_argument("--name", help="Site display name (used with --add).")
    parser.add_argument("--terms-url", help="Terms of Service URL (used with --add).")
    parser.add_argument("--privacy-url", help="Privacy Policy URL (used with --add).")
    args = parser.parse_args()

    if args.add:
        if not args.name or not (args.terms_url or args.privacy_url):
            print("ERROR: --add requires --name and at least one of --terms-url/--privacy-url")
            sys.exit(1)
        domain = normalize_domain(args.add)
        print(f"\n=== Adding {args.name} ({domain}) ===")
        try:
            result = add_and_build_site(domain, args.name, args.terms_url, args.privacy_url)
        except PlaywrightUnavailableError as exc:
            print(f"ERROR: {exc}")
            sys.exit(1)
        print(f"  Saved to {CACHE_DIR / domain}" if result["cached"] else "  Nothing was cached.")
        return

    configs = load_site_configs()
    if not configs:
        print(f"No site configs found under {SOURCES_DIR}. See its README.md.")
        sys.exit(1)

    target_domain = normalize_domain(args.only) if args.only else None
    if target_domain:
        if target_domain not in configs:
            print(f"ERROR: '{target_domain}' is not configured under {SOURCES_DIR}")
            sys.exit(1)
        configs = {target_domain: configs[target_domain]}

    try:
        for domain, config in configs.items():
            print(f"\n=== {config['site_name']} ({domain}) ===")
            result = build_one_site(domain, config)
            print(f"  Saved to {CACHE_DIR / domain}" if result["cached"] else "  Nothing was cached.")
    except PlaywrightUnavailableError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    print(f"\nDone. Cache lives under {CACHE_DIR}")


if __name__ == "__main__":
    main()
