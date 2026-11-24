# Real-site demo cache sources

Each file here describes ONE real website to pre-cache for the "Scan This
Website" dashboard feature. To add a new site, drop in a new JSON file
(any filename works, but `<domain>.json` is the convention) shaped like
this:

```json
{
  "domain": "example.com",
  "site_name": "Example Inc.",
  "pages": {
    "terms": "https://example.com/terms",
    "privacy": "https://example.com/privacy"
  }
}
```

- `domain` must match what appears in the browser address bar (no `www.`,
  no `https://`) - this is the key the extension looks up when you click
  "Scan" on that site.
- `pages` may include `terms`, `privacy`, or both. At least one is required.

Then run:

```bash
python backend/scripts/build_realsite_cache.py
```

This renders every configured URL with a real headless browser (so it
works even for JavaScript-heavy sites), extracts clause-like text, and
writes the result to `backend/data/realsite_cache/<domain>/`. Nothing is
classified at this stage - predictions always happen live when a student
clicks "Scan" in the extension, using whichever model is currently trained.

To (re)build just one site instead of all of them:

```bash
python backend/scripts/build_realsite_cache.py --only example.com
```

To scaffold AND build a brand-new site in one step, without hand-writing
JSON:

```bash
python backend/scripts/build_realsite_cache.py --add example.com \
  --name "Example Inc." \
  --terms-url "https://example.com/terms" \
  --privacy-url "https://example.com/privacy"
```
