"""Best-effort verification of the click-to-scan dashboard against REAL
external sites with real network access. Separate from the deterministic
fixture-based tests, since this depends on live internet and the current
structure of third-party websites. Run manually/opportunistically.
"""
from __future__ import annotations

import pytest


def _scan_via_popup_and_get_dashboard(browser_context, extension_id, site_url):
    site_page = browser_context.new_page()
    site_page.goto(site_url, timeout=30000, wait_until="domcontentloaded")
    site_page.bring_to_front()

    popup = browser_context.new_page()
    popup.goto(f"chrome-extension://{extension_id}/popup.html")
    site_page.bring_to_front()
    popup.reload()  # see note in test_06_realsite_dashboard.py about popup-as-tab focus timing

    with browser_context.expect_page(timeout=20000) as new_page_info:
        popup.locator("#cg-scan-site").click()
    dashboard = new_page_info.value
    popup.close()
    site_page.close()
    return dashboard


@pytest.mark.parametrize("url", ["https://github.com", "https://www.facebook.com"])
def test_visiting_real_site_never_auto_pops_up(page, url):
    page.goto(url, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    assert page.locator("#cg-attention-popup").count() == 0


@pytest.mark.parametrize("url", ["https://github.com", "https://www.facebook.com"])
def test_scan_button_produces_real_dashboard(browser_context, extension_id, url):
    dashboard = _scan_via_popup_and_get_dashboard(browser_context, extension_id, url)
    try:
        dashboard.wait_for_selector(".cg-grade-badge", timeout=20000)
        grade_text = dashboard.locator(".cg-grade-badge").inner_text()
        assert grade_text.strip() in {"A", "B", "C", "D"}
        assert "live, just now" in dashboard.locator(".cg-meta-card").inner_text()
    finally:
        dashboard.close()
