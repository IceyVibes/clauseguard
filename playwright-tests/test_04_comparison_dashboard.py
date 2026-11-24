"""Comparison dashboard: cross-scenario summaries, with no PII leakage."""
from __future__ import annotations

from conftest import DEMO_URL


def test_comparison_dashboard_reflects_scans_without_storing_clause_text(page):
    # Produce a fresh scan so the dashboard has at least one row.
    page.goto(f"{DEMO_URL}/shopping.html")
    page.locator("#cg-scan-button").click()
    page.wait_for_selector("#cg-panel-status:has-text('Scan complete.')", timeout=15000)

    stored_raw = page.evaluate("localStorage.getItem('clauseguard_scan_results')")
    assert stored_raw is not None
    assert "QuickCart" in stored_raw

    # Privacy guarantee: the persisted summary must never contain the
    # original clause sentences or any fake signup field values.
    for forbidden in [
        "renews automatically every year",
        "Jordan",
        "jordan@example.com",
    ]:
        assert forbidden not in stored_raw

    page.goto(f"{DEMO_URL}/comparison.html")
    rows = page.locator("#cg-compare-body tr")
    assert rows.count() >= 1
    assert "QuickCart Plus" in page.locator("#cg-compare-body").inner_text()
    assert "%" in page.locator("#cg-compare-body").inner_text()


def test_reset_demo_results_clears_dashboard(page):
    page.goto(f"{DEMO_URL}/shopping.html")
    page.locator("#cg-scan-button").click()
    page.wait_for_selector("#cg-panel-status:has-text('Scan complete.')", timeout=15000)

    page.goto(f"{DEMO_URL}/comparison.html")
    page.locator("#cg-reset-btn").click()

    assert page.locator("#cg-empty-state").is_visible()
    assert page.evaluate("localStorage.getItem('clauseguard_scan_results')") is None
