"""API tests for the ClauseGuard backend.

These tests exercise the real trained local model (MiniLM + LogisticRegression).
Run `python backend/scripts/train_model.py` first if backend/models/ is empty;
otherwise these tests will fail with a 503 "model not loaded" style error.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas import MAX_BATCH_SIZE

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
MODEL_READY = (
    (MODELS_DIR / "clause_classifier.joblib").exists()
    and (MODELS_DIR / "minilm").exists()
    and (MODELS_DIR / "model_metadata.json").exists()
)

pytestmark = pytest.mark.skipif(
    not MODEL_READY,
    reason="Model artifacts missing. Run 'python backend/scripts/train_model.py' first.",
)

client = TestClient(app)

PERMITTED_LABELS = {"SAFE", "PRIVACY_RISK", "PAYMENT_RISK", "USER_RIGHTS_RISK"}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["model_loaded"] is True


def test_model_info():
    response = client.get("/model-info")
    assert response.status_code == 200
    body = response.json()
    assert body["encoder_name"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert set(body["class_names"]) == PERMITTED_LABELS
    assert body["dataset_size"] > 0
    assert 0.0 <= body["test_accuracy"] <= 1.0


def test_predict_valid_input():
    response = client.post(
        "/predict",
        json={"text": "Your subscription will renew automatically every month."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["label"] in PERMITTED_LABELS
    assert 0.0 <= body["confidence"] <= 1.0
    assert isinstance(body["is_attention_required"], bool)
    assert body["friendly_label"]
    assert body["message"]


def test_predict_empty_input():
    response = client.post("/predict", json={"text": "   "})
    assert response.status_code == 422


def test_predict_batch():
    clauses = [
        "You may cancel your account at any time.",
        "We may share personal information with advertising partners.",
        "Your subscription automatically renews each month.",
    ]
    response = client.post("/predict-batch", json={"clauses": clauses})
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == len(clauses)
    assert body["summary"]["total_clauses"] == len(clauses)
    for result in body["results"]:
        assert result["label"] in PERMITTED_LABELS
        assert 0.0 <= result["confidence"] <= 1.0


def test_predict_batch_empty_list_rejected():
    response = client.post("/predict-batch", json={"clauses": []})
    assert response.status_code == 422


def test_predict_batch_maximum_validation():
    too_many = ["Example clause."] * (MAX_BATCH_SIZE + 1)
    response = client.post("/predict-batch", json={"clauses": too_many})
    assert response.status_code == 422


def test_predict_batch_within_maximum_allowed():
    exactly_max = ["Example clause about cancellation and refunds."] * MAX_BATCH_SIZE
    response = client.post("/predict-batch", json={"clauses": exactly_max})
    assert response.status_code == 200
    assert len(response.json()["results"]) == MAX_BATCH_SIZE


def test_predict_rejects_clause_too_long():
    response = client.post("/predict", json={"text": "x" * 2001})
    assert response.status_code == 422


@pytest.mark.parametrize(
    "text,expected_min_confidence",
    [
        ("Your subscription will renew automatically every month.", 0.0),
        ("You may cancel your account at any time.", 0.0),
    ],
)
def test_predict_confidence_bounds(text, expected_min_confidence):
    response = client.post("/predict", json={"text": text})
    assert response.status_code == 200
    confidence = response.json()["confidence"]
    assert expected_min_confidence <= confidence <= 1.0


def test_realsite_cache_list_includes_known_domains():
    response = client.get("/realsite-cache")
    assert response.status_code == 200
    domains = response.json()["domains"]
    assert "github.com" in domains


def test_realsite_cache_hit_returns_clauses():
    response = client.get("/realsite-cache/github.com")
    assert response.status_code == 200
    body = response.json()
    assert body["domain"] == "github.com"
    assert "terms" in body["pages"]
    assert len(body["pages"]["terms"]["clauses"]) > 0


def test_realsite_cache_normalizes_www_prefix():
    response = client.get("/realsite-cache/www.github.com")
    assert response.status_code == 200


def test_realsite_cache_miss_returns_404():
    response = client.get("/realsite-cache/this-domain-does-not-exist.example")
    assert response.status_code == 404


def test_build_realsite_cache_rejects_missing_urls():
    response = client.post(
        "/realsite-cache/build",
        json={"domain": "example.com", "site_name": "Example"},
    )
    assert response.status_code == 422


try:
    import playwright  # noqa: F401

    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False


@pytest.mark.skipif(not _PLAYWRIGHT_AVAILABLE, reason="playwright not installed (dev-only dependency)")
def test_build_realsite_cache_end_to_end():
    """Exercises the full admin 'add a site' flow against a small, stable
    real page, then cleans up the cache entry it creates."""
    import shutil

    from backend.app.realsite_builder import CACHE_DIR, SOURCES_DIR

    test_domain = "example.com"
    try:
        response = client.post(
            "/realsite-cache/build",
            json={
                "domain": test_domain,
                "site_name": "Example Domain (test)",
                "terms_url": "https://example.com/",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["cached"] is True
        assert body["pages"]["terms"]["clause_count"] > 0

        cache_response = client.get(f"/realsite-cache/{test_domain}")
        assert cache_response.status_code == 200
    finally:
        shutil.rmtree(CACHE_DIR / test_domain, ignore_errors=True)
        (SOURCES_DIR / f"{test_domain}.json").unlink(missing_ok=True)
