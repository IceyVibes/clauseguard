"""End-to-end scenario walkthroughs, simulating a real user on each fictional
demo site: read the offer, notice the Terms, tick the checkbox, then use the
ClauseGuard extension to scan before accepting.
"""
from __future__ import annotations

import re

import pytest
from conftest import DEMO_URL

SCENARIOS = [
    "streaming.html",
    "shopping.html",
    "fitness.html",
    "gaming.html",
    "cloud-storage.html",
    "student-learning.html",
]


@pytest.mark.parametrize("scenario_file", SCENARIOS)
def test_checkbox_gates_primary_button_and_shows_nudge(page, scenario_file):
    page.goto(f"{DEMO_URL}/{scenario_file}")

    reading_time = page.locator("#cg-reading-time")
    assert re.search(r"Estimated reading time: \d+ minute", reading_time.inner_text())

    primary_button = page.locator("#cg-primary-action")
    assert primary_button.is_disabled()

    checkbox = page.locator("#cg-accept-checkbox")
    checkbox.check()
    assert primary_button.is_enabled()

    nudge = page.locator("#cg-review-nudge")
    assert "Have you reviewed them?" in nudge.inner_text()

    # Elapsed timer text should have stopped incrementing once checked.
    timer_text_after_check = page.locator("#cg-elapsed-timer").inner_text()
    page.wait_for_timeout(1500)
    assert page.locator("#cg-elapsed-timer").inner_text() == timer_text_after_check


@pytest.mark.parametrize("scenario_file", SCENARIOS[:2])
def test_checking_checkbox_alone_auto_triggers_scan_and_popup(page, scenario_file):
    """The core requested behaviour: ticking 'I have reviewed the Terms'
    automatically runs the AI scan (no manual click on the floating button
    needed), and a prominent popup summarizes the result."""
    page.goto(f"{DEMO_URL}/{scenario_file}")
    clause_count = page.locator(".tc-clause").count()

    # Deliberately do NOT click #cg-scan-button here.
    page.locator("#cg-accept-checkbox").check()

    page.wait_for_selector("#cg-attention-popup:not(.cg-hidden)", timeout=15000)
    popup_text = page.locator("#cg-attention-popup").inner_text()
    assert ("may need your attention" in popup_text) or ("No prototype warning" in popup_text)

    # The underlying scan must have actually run: every clause badged/highlighted.
    assert page.locator(".tc-clause .cg-badge").count() == clause_count


@pytest.mark.parametrize("scenario_file", SCENARIOS)
def test_scan_highlights_every_clause_and_matches_side_panel(page, scenario_file):
    page.goto(f"{DEMO_URL}/{scenario_file}")

    clauses = page.locator(".tc-clause")
    clause_count = clauses.count()
    assert clause_count >= 10

    scan_button = page.locator("#cg-scan-button")
    scan_button.wait_for(state="visible", timeout=10000)
    scan_button.click()

    page.wait_for_selector("#cg-panel-status:has-text('Scan complete.')", timeout=15000)

    # Every clause should carry exactly one badge (no duplicates).
    badges = page.locator(".tc-clause .cg-badge")
    assert badges.count() == clause_count

    highlighted = page.locator(
        ".tc-clause.cg-highlight-safe, .tc-clause.cg-highlight-privacy, "
        ".tc-clause.cg-highlight-payment, .tc-clause.cg-highlight-rights"
    )
    assert highlighted.count() == clause_count

    stats_text = page.locator("#cg-panel-stats").inner_text()
    assert f"Clauses reviewed: {clause_count}" in stats_text

    score_text = page.locator("#cg-panel-score").inner_text()
    assert "Prototype attention score" in score_text


@pytest.mark.parametrize("scenario_file", SCENARIOS[:2])
def test_rescanning_does_not_duplicate_badges(page, scenario_file):
    page.goto(f"{DEMO_URL}/{scenario_file}")
    clause_count = page.locator(".tc-clause").count()

    scan_button = page.locator("#cg-scan-button")
    scan_button.click()
    page.wait_for_selector("#cg-panel-status:has-text('Scan complete.')", timeout=15000)

    scan_button.click()
    page.wait_for_selector("#cg-panel-status:has-text('Scan complete.')", timeout=15000)

    assert page.locator(".tc-clause .cg-badge").count() == clause_count
    assert page.locator(".tc-clause .cg-badge-explanation").count() == clause_count


@pytest.mark.parametrize("scenario_file", SCENARIOS[:1])
def test_clear_results_restores_neutral_presentation(page, scenario_file):
    page.goto(f"{DEMO_URL}/{scenario_file}")

    page.locator("#cg-scan-button").click()
    page.wait_for_selector("#cg-panel-status:has-text('Scan complete.')", timeout=15000)
    assert page.locator(".tc-clause .cg-badge").count() > 0

    page.locator("#cg-clear-results").click()
    assert page.locator(".tc-clause .cg-badge").count() == 0
    assert page.locator(".tc-clause.cg-highlight-safe").count() == 0
    assert page.locator("#cg-panel-stats").inner_text().strip() == ""


@pytest.mark.parametrize("scenario_file", SCENARIOS[:1])
def test_show_only_flagged_hides_safe_clauses(page, scenario_file):
    page.goto(f"{DEMO_URL}/{scenario_file}")
    total = page.locator(".tc-clause").count()

    page.locator("#cg-scan-button").click()
    page.wait_for_selector("#cg-panel-status:has-text('Scan complete.')", timeout=15000)

    safe_count = page.locator(".tc-clause.cg-highlight-safe").count()
    page.locator("#cg-only-flagged").check()

    visible_clauses = page.locator(".tc-clause:visible")
    assert visible_clauses.count() == total - safe_count


@pytest.mark.parametrize("scenario_file", SCENARIOS[:1])
def test_model_details_shows_measured_accuracy(page, scenario_file):
    page.goto(f"{DEMO_URL}/{scenario_file}")
    page.locator("#cg-scan-button").click()
    page.wait_for_selector("#cg-panel-status:has-text('Scan complete.')", timeout=15000)

    page.locator("#cg-model-details").click()
    details_box = page.locator("#cg-model-details-box")
    page.wait_for_selector("#cg-model-details-box:has-text('Encoder')", timeout=10000)
    details_text = details_box.inner_text()
    assert "Encoder" in details_text
    assert "Measured test accuracy" in details_text
    assert "sentence-transformers/all-MiniLM-L6-v2" in details_text
