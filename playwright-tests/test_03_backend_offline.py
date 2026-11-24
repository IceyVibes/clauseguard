"""Backend-offline handling: the extension must never fabricate results."""
from __future__ import annotations

import subprocess
import time

from conftest import DEMO_URL, REPO_ROOT


def _wait_for_health(expect_up: bool, timeout_s: float = 10.0) -> bool:
    import urllib.request
    import urllib.error

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1) as resp:
                if expect_up and resp.status == 200:
                    return True
        except Exception:
            if not expect_up:
                return True
        time.sleep(0.3)
    return False


def test_scan_shows_offline_message_when_backend_unreachable(page):
    # Find and stop the real uvicorn process so this is a genuine offline check.
    result = subprocess.run(
        ["pgrep", "-f", "uvicorn backend.app.main:app"],
        capture_output=True,
        text=True,
    )
    pids = [p for p in result.stdout.split() if p]
    assert pids, "Expected the backend uvicorn process to be running before this test."

    subprocess.run(["kill"] + pids)
    assert _wait_for_health(expect_up=False, timeout_s=10), "Backend did not stop in time."

    try:
        page.goto(f"{DEMO_URL}/streaming.html")
        page.locator("#cg-scan-button").click()
        page.wait_for_selector(
            "#cg-panel-status:has-text('could not reach the local analysis service')",
            timeout=15000,
        )

        # No clause should have been (falsely) highlighted or badged.
        assert page.locator(".tc-clause .cg-badge").count() == 0
    finally:        # Restart the backend so subsequent tests (and the user's manual
        # testing afterwards) still have a working local service.
        subprocess.Popen(
            [
                str(REPO_ROOT / ".venv" / "bin" / "uvicorn"),
                "backend.app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=str(REPO_ROOT),
            stdout=open("/tmp/uvicorn.log", "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        assert _wait_for_health(expect_up=True, timeout_s=20), "Backend did not restart in time."


def test_checking_checkbox_shows_offline_popup_without_fabricating_results(page):
    """Ticking the Terms checkbox now auto-triggers a scan. If the backend
    is down at that moment, the popup must say so honestly instead of
    inventing a result."""
    result = subprocess.run(
        ["pgrep", "-f", "uvicorn backend.app.main:app"],
        capture_output=True,
        text=True,
    )
    pids = [p for p in result.stdout.split() if p]
    assert pids, "Expected the backend uvicorn process to be running before this test."

    subprocess.run(["kill"] + pids)
    assert _wait_for_health(expect_up=False, timeout_s=10), "Backend did not stop in time."

    try:
        page.goto(f"{DEMO_URL}/shopping.html")
        page.locator("#cg-accept-checkbox").check()

        page.wait_for_selector("#cg-attention-popup:not(.cg-hidden)", timeout=15000)
        popup_text = page.locator("#cg-attention-popup").inner_text()
        assert "could not check these terms" in popup_text
        assert page.locator(".tc-clause .cg-badge").count() == 0
    finally:
        subprocess.Popen(
            [
                str(REPO_ROOT / ".venv" / "bin" / "uvicorn"),
                "backend.app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=str(REPO_ROOT),
            stdout=open("/tmp/uvicorn.log", "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        assert _wait_for_health(expect_up=True, timeout_s=20), "Backend did not restart in time."
