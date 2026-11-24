"""Lightweight structural validation for the ClauseGuard repository.

These tests do not require the trained model and can run even before
``train_model.py`` has been executed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTENSION_DIR = REPO_ROOT / "extension"
DEMO_DIR = REPO_ROOT / "demo"

REQUIRED_DEMO_FILES = [
    "index.html",
    "streaming.html",
    "shopping.html",
    "fitness.html",
    "gaming.html",
    "cloud-storage.html",
    "student-learning.html",
    "comparison.html",
    "presentation.html",
    "admin-add-site.html",
    "styles.css",
    "demo.js",
    "serve_demo.py",
]

SCENARIO_PAGES = [
    "streaming.html",
    "shopping.html",
    "fitness.html",
    "gaming.html",
    "cloud-storage.html",
    "student-learning.html",
]


def test_manifest_json_is_valid():
    manifest_path = EXTENSION_DIR / "manifest.json"
    assert manifest_path.exists(), "extension/manifest.json is missing"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data.get("manifest_version") == 3
    assert "name" in data
    assert "version" in data


def test_required_demo_files_exist():
    missing = [name for name in REQUIRED_DEMO_FILES if not (DEMO_DIR / name).exists()]
    assert not missing, f"Missing demo files: {missing}"


def test_every_scenario_page_contains_tc_clause():
    for name in SCENARIO_PAGES:
        html = (DEMO_DIR / name).read_text(encoding="utf-8")
        matches = re.findall(r'class="tc-clause"', html)
        assert len(matches) >= 10, f"{name} should contain at least 10 .tc-clause elements"

        clause_ids = re.findall(r'data-clause-id="([^"]+)"', html)
        assert len(clause_ids) == len(set(clause_ids)), f"{name} has duplicate data-clause-id values"
