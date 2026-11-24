"""Tests for the click-to-scan dashboard workflow (NOT automatic). The
extension must never scan or pop up anything on its own - only when the
user explicitly opens the popup and clicks "Scan Terms & Privacy Policy".

Uses a test-only cache entry under backend/data/realsite_cache/127.0.0.1/,
built from the same content as demo/_fixtures/, so results are deterministic
without depending on live internet access.
"""
from __future__ import annotations

from conftest import DEMO_URL


def _bring_site_tab_to_front_and_open_popup(browser_context, extension_id, site_url):
    site_page = browser_context.new_page()
    site_page.goto(site_url)
    site_page.bring_to_front()

    popup = browser_context.new_page()
    popup.goto(f"chrome-extension://{extension_id}/popup.html")
    site_page.bring_to_front()  # popup must not become the "active" tab
    return site_page, popup


def test_visiting_any_page_never_auto_scans_or_pops_up(page):
    """No content script runs on arbitrary pages anymore - visiting a
    cached-domain-equivalent page must not show any VISIBLE popup by
    itself. (content.js, which only runs on our own demo origin, still
    creates a hidden popup container as part of its own init - that's fine,
    it just must never become visible without a user click.)"""
    page.goto(f"{DEMO_URL}/_fixtures/homepage.html")
    page.wait_for_timeout(2000)
    popup = page.locator("#cg-attention-popup")
    assert popup.count() == 0 or not popup.is_visible()


def test_scan_button_shows_current_domain_in_popup(browser_context, extension_id):
    site_page, popup = _bring_site_tab_to_front_and_open_popup(
        browser_context, extension_id, f"{DEMO_URL}/_fixtures/homepage.html"
    )
    try:
        # A real extension popup is never itself "the active tab" (it's an
        # anchored overlay, not a tab). Our test simulates it as a regular
        # tab, so opening it can transiently steal "active" status; reload
        # once focus has settled back on the site tab, matching what a real
        # popup always sees.
        popup.reload()
        popup.wait_for_selector("#cg-current-domain:has-text('127.0.0.1')", timeout=10000)
    finally:
        popup.close()
        site_page.close()


def test_scan_cached_domain_opens_dashboard_with_grade(browser_context, extension_id):
    site_page, popup = _bring_site_tab_to_front_and_open_popup(
        browser_context, extension_id, f"{DEMO_URL}/_fixtures/homepage.html"
    )
    try:
        with browser_context.expect_page(timeout=15000) as new_page_info:
            popup.locator("#cg-scan-site").click()
        dashboard = new_page_info.value
        dashboard.wait_for_selector(".cg-grade-badge", timeout=15000)

        grade_text = dashboard.locator(".cg-grade-badge").inner_text()
        assert grade_text.strip() in {"A", "B", "C", "D"}

        meta_text = dashboard.locator(".cg-meta-card").inner_text()
        assert "live, just now" in meta_text
        assert "seconds" in meta_text

        # The grade legend must explain all four bands in plain language,
        # and highlight whichever one applies to this site.
        legend_text = dashboard.locator(".cg-grade-legend").inner_text()
        for expected in ["% flagged", "Mostly user-friendly", "need careful review"]:
            assert expected in legend_text
        assert dashboard.locator(".cg-grade-legend-current").count() == 1

        dashboard.close()
    finally:
        popup.close()
        site_page.close()


def test_scan_uncached_domain_shows_friendly_message_no_dashboard(browser_context, extension_id):
    # "localhost" is intentionally NOT in the test cache (only "127.0.0.1" is),
    # so this exercises the cache-miss path.
    site_page, popup = _bring_site_tab_to_front_and_open_popup(
        browser_context, extension_id, f"http://localhost:5500/_fixtures/homepage.html"
    )
    try:
        popup.locator("#cg-scan-site").click()
        popup.wait_for_selector("#cg-scan-status:has-text('No cached demo data')", timeout=15000)
    finally:
        popup.close()
        site_page.close()
