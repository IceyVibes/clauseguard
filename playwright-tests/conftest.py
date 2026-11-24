"""Shared Playwright fixtures for ClauseGuard end-to-end tests.

These tests load the REAL unpacked extension from extension/ into a
persistent Chromium context, exactly as a user would via
chrome://extensions "Load unpacked". No mocking of the extension or the
backend is used: the FastAPI service and demo server must already be
running (see playwright-tests/README.md).
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
EXTENSION_PATH = REPO_ROOT / "extension"
BACKEND_URL = "http://127.0.0.1:8000"
DEMO_URL = "http://127.0.0.1:5500"


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser_context(playwright_instance):
    user_data_dir = tempfile.mkdtemp(prefix="clauseguard-pw-profile-")
    context = playwright_instance.chromium.launch_persistent_context(
        user_data_dir,
        headless=False,
        args=[
            f"--disable-extensions-except={EXTENSION_PATH}",
            f"--load-extension={EXTENSION_PATH}",
            "--no-first-run",
        ],
    )
    yield context
    context.close()
    shutil.rmtree(user_data_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def extension_id(browser_context):
    page = browser_context.new_page()
    page.goto("chrome://extensions")
    page.locator("extensions-item").first.wait_for(state="attached", timeout=15000)
    ext_id = page.locator("extensions-item").first.get_attribute("id")
    page.close()
    assert ext_id, "Could not determine the loaded extension's ID."
    return ext_id


@pytest.fixture()
def page(browser_context):
    p = browser_context.new_page()
    yield p
    p.close()
