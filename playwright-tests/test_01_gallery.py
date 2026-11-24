"""Gallery (index.html) behaviour: cards, navigation, Judge Mode persistence."""
from __future__ import annotations

from conftest import DEMO_URL

SCENARIO_LINKS = [
    "streaming.html",
    "shopping.html",
    "fitness.html",
    "gaming.html",
    "cloud-storage.html",
    "student-learning.html",
]


def test_gallery_shows_six_scenario_cards(page):
    page.goto(f"{DEMO_URL}/index.html")
    cards = page.locator(".cg-card")
    assert cards.count() == 6


def test_gallery_links_point_to_each_scenario(page):
    page.goto(f"{DEMO_URL}/index.html")
    hrefs = page.locator(".cg-card a.cg-btn").evaluate_all("els => els.map(e => e.getAttribute('href'))")
    assert sorted(hrefs) == sorted(SCENARIO_LINKS)


def test_judge_mode_toggle_persists_and_shows_banner_on_scenario(page):
    page.goto(f"{DEMO_URL}/index.html")
    checkbox = page.locator("#cg-judge-toggle-checkbox")
    assert not checkbox.is_checked()

    checkbox.check()
    banner = page.locator("#cg-judge-bar-top")
    assert "Judge Mode" in banner.inner_text()

    # Navigate to a scenario; Judge Mode should still be visible there too.
    page.goto(f"{DEMO_URL}/streaming.html")
    scenario_banner = page.locator("#cg-judge-banner")
    assert "Judge Mode" in scenario_banner.inner_text()

    # Turn it back off and confirm the banner disappears on a fresh load.
    page.goto(f"{DEMO_URL}/index.html")
    page.locator("#cg-judge-toggle-checkbox").uncheck()
    page.goto(f"{DEMO_URL}/streaming.html")
    assert not page.locator("#cg-judge-banner").is_visible()
