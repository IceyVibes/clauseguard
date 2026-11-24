"""Model loading and inference logic for ClauseGuard.

Loads the local MiniLM sentence encoder and the student-trained
LogisticRegression classifier once at process startup, then exposes
simple, cautious classification helpers used by the FastAPI routes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import joblib

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
MODELS_DIR = BACKEND_DIR / "models"
CLASSIFIER_PATH = MODELS_DIR / "clause_classifier.joblib"
ENCODER_DIR = MODELS_DIR / "minilm"
METADATA_PATH = MODELS_DIR / "model_metadata.json"

FRIENDLY_LABELS: Dict[str, str] = {
    "SAFE": "No prototype warning",
    "PRIVACY_RISK": "Privacy attention",
    "PAYMENT_RISK": "Payment attention",
    "USER_RIGHTS_RISK": "User-rights attention",
}

MESSAGES: Dict[str, str] = {
    "SAFE": "No prototype attention category was detected for this clause.",
    "PRIVACY_RISK": (
        "This clause may contain conditions about personal information, "
        "tracking, retention or third-party data use."
    ),
    "PAYMENT_RISK": (
        "This clause may contain renewal, payment, fee, cancellation or "
        "refund conditions."
    ),
    "USER_RIGHTS_RISK": (
        "This clause may contain conditions affecting dispute handling, "
        "account control, service changes or rights over submitted content."
    ),
}

SUMMARY_KEY_BY_LABEL: Dict[str, str] = {
    "SAFE": "safe",
    "PRIVACY_RISK": "privacy_attention",
    "PAYMENT_RISK": "payment_attention",
    "USER_RIGHTS_RISK": "user_rights_attention",
}


class ModelNotLoadedError(RuntimeError):
    """Raised when model artifacts are missing or fail to load."""


class ModelService:
    """Loads the encoder + classifier once and serves predictions."""

    def __init__(self) -> None:
        self._encoder = None
        self._classifier = None
        self._metadata: Dict | None = None
        self._load_error: str | None = None
        self._load()

    def _load(self) -> None:
        missing = [
            str(path)
            for path in (CLASSIFIER_PATH, ENCODER_DIR, METADATA_PATH)
            if not path.exists()
        ]
        if missing:
            self._load_error = (
                "Model artifacts not found: "
                f"{', '.join(missing)}. Run 'python backend/scripts/train_model.py' "
                "before starting the API."
            )
            return

        try:
            from sentence_transformers import SentenceTransformer

            self._encoder = SentenceTransformer(str(ENCODER_DIR))
            self._classifier = joblib.load(CLASSIFIER_PATH)
            self._metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - surfaced via /health and errors
            self._load_error = f"Failed to load model artifacts: {exc}"

    @property
    def is_loaded(self) -> bool:
        return self._encoder is not None and self._classifier is not None

    @property
    def load_error(self) -> str | None:
        return self._load_error

    @property
    def metadata(self) -> Dict:
        if self._metadata is None:
            raise ModelNotLoadedError(self._load_error or "Model metadata unavailable.")
        return self._metadata

    def _require_loaded(self) -> None:
        if not self.is_loaded:
            raise ModelNotLoadedError(
                self._load_error
                or "Model is not loaded. Run train_model.py and restart the API."
            )

    def classify_one(self, text: str) -> Dict:
        self._require_loaded()
        embedding = self._encoder.encode([text], show_progress_bar=False)
        probabilities = self._classifier.predict_proba(embedding)[0]
        classes = self._classifier.classes_
        best_index = int(probabilities.argmax())
        label = str(classes[best_index])
        confidence = float(probabilities[best_index])

        return {
            "text": text,
            "label": label,
            "confidence": round(confidence, 4),
            "is_attention_required": label != "SAFE",
            "friendly_label": FRIENDLY_LABELS[label],
            "message": MESSAGES[label],
        }

    def classify_batch(self, texts: List[str]) -> List[Dict]:
        self._require_loaded()
        return [self.classify_one(text) for text in texts]

    @staticmethod
    def build_summary(results: List[Dict]) -> Dict:
        summary = {
            "total_clauses": len(results),
            "attention_required": 0,
            "safe": 0,
            "privacy_attention": 0,
            "payment_attention": 0,
            "user_rights_attention": 0,
        }
        for result in results:
            key = SUMMARY_KEY_BY_LABEL[result["label"]]
            summary[key] += 1
            if result["is_attention_required"]:
                summary["attention_required"] += 1
        return summary


model_service = ModelService()
