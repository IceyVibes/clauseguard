"""Extension popup: backend/model status, and the real-website reality-test
feature (analyzing a user's text selection on any page via activeTab).
"""
from __future__ import annotations

from conftest import DEMO_URL


def test_popup_reports_backend_online_and_model_loaded(browser_context, extension_id):
    popup = browser_context.new_page()
    try:
        popup.goto(f"chrome-extension://{extension_id}/popup.html")
        popup.wait_for_selector("#cg-backend-status:has-text('Online')", timeout=10000)
        popup.wait_for_selector("#cg-model-status:has-text('Loaded')", timeout=10000)
    finally:
        popup.close()


def test_analyze_selected_text_on_a_real_looking_page(browser_context, extension_id):
    """Simulates the 'reality test' workflow: select text on any page, then
    use the popup's 'Analyze Selected Text' button (no .tc-clause markup
    required, unlike the automatic demo-site scan)."""
    content_page = browser_context.new_page()
    content_page.goto(f"{DEMO_URL}/streaming.html")

    # Select the text of the first clause, just like a real user highlighting
    # a paragraph of a real Terms of Service page with their mouse.
    content_page.evaluate(
        """
        () => {
          const el = document.querySelector('.tc-clause');
          const range = document.createRange();
          range.selectNodeContents(el);
          const selection = window.getSelection();
          selection.removeAllRanges();
          selection.addRange(range);
        }
        """
    )
    selected_text = content_page.evaluate("window.getSelection().toString()")
    assert selected_text.strip() != ""

    popup = browser_context.new_page()
    try:
        popup.goto(f"chrome-extension://{extension_id}/popup.html")

        # Make sure the demo tab (not the popup tab) is the "active" tab,
        # matching real popup behaviour where the popup overlays the toolbar
        # without changing the active tab.
        content_page.bring_to_front()

        popup.locator("#cg-analyze-selection").click()
        popup.wait_for_selector(
            "#cg-selection-results .cg-selection-result-item", timeout=15000
        )

        results_text = popup.locator("#cg-selection-results").inner_text()
        assert "Summary:" in results_text
        assert "confidence" in results_text
    finally:
        popup.close()
        content_page.close()
