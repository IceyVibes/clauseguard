# ClauseGuard - Playwright end-to-end tests

These tests drive the REAL unpacked extension in a real (headed) Chromium
browser via Playwright's persistent-context extension loading, against the
real FastAPI backend and real demo HTTP server. Nothing is mocked.

## Prerequisites

From the `clauseguard/` directory, with the virtual environment active:

```bash
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install pytest-playwright
playwright install chromium
python backend/scripts/train_model.py   # only needed once
```

Start the two local services (each in its own terminal, or backgrounded):

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 &
python demo/serve_demo.py &
```

## Run the tests

```bash
python -m pytest playwright-tests -v
```

A visible Chromium window will open (extensions generally cannot be loaded
in headless mode), and you will see the browser navigate between the demo
scenario pages automatically. This is expected.

## What is covered

- `test_01_gallery.py` - Scenario Lab cards, navigation, Judge Mode toggle persistence.
- `test_02_scenario_flow.py` - per-scenario: reading-time estimate, checkbox
  gating the primary button, review nudge, **ticking the checkbox alone
  auto-triggers a full scan and an attention popup** (no button click
  needed), scanning highlights every clause, no duplicate badges on
  rescanning, Clear Results, Show only flagged, Model Details.
- `test_03_backend_offline.py` - stops the real backend process and verifies
  the extension shows the official offline message instead of fabricating results,
  then restarts the backend. Also verifies the checkbox-triggered auto-scan
  shows the same honest offline popup rather than a fabricated result.
- `test_04_comparison_dashboard.py` - cross-scenario summary storage, and
  verifies no clause text or fake signup field values ever reach `localStorage`.
- `test_05_popup.py` - popup backend/model status pills, and the
  "Analyze Selected Text" reality-test feature used for testing on real websites.
- `test_06_realsite_dashboard.py` - the click-to-scan dashboard feature:
  confirms NOTHING scans automatically on any page, the popup shows the
  current domain, clicking Scan on a cached domain opens a dashboard tab
  with a real-time-computed grade, and an uncached domain shows an honest
  "not cached yet" message. Uses a test-only cache entry under
  `backend/data/realsite_cache/127.0.0.1/` (same content as
  `demo/_fixtures/`) so results are deterministic without live internet.
- `test_07_realsite_live.py` - the same checks against REAL external sites
  (github.com, facebook.com) with real network access: no auto-popup, and
  Scan produces a real dashboard with a real grade. Not required for CI
  since it depends on live internet and third-party site structure, but
  confirms the feature genuinely works against real-world sites.
