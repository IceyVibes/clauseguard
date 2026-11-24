"""Pydantic request/response schemas for the ClauseGuard backend."""
from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field, field_validator

MAX_CLAUSE_LENGTH = 2000
MAX_BATCH_SIZE = 100


class PredictRequest(BaseModel):
    text: str = Field(..., description="A single Terms and Conditions clause.")

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Clause text must not be empty.")
        if len(cleaned) > MAX_CLAUSE_LENGTH:
            raise ValueError(
                f"Clause text must be {MAX_CLAUSE_LENGTH} characters or fewer."
            )
        return cleaned


class PredictResponse(BaseModel):
    text: str
    label: str
    confidence: float
    is_attention_required: bool
    friendly_label: str
    message: str


class BatchPredictRequest(BaseModel):
    clauses: List[str] = Field(..., description="A list of clause texts to classify.")

    @field_validator("clauses")
    @classmethod
    def validate_clauses(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("At least one clause must be provided.")
        if len(value) > MAX_BATCH_SIZE:
            raise ValueError(f"A batch may contain at most {MAX_BATCH_SIZE} clauses.")

        cleaned: List[str] = []
        for clause in value:
            stripped = clause.strip()
            if not stripped:
                raise ValueError("Clause text must not be empty.")
            if len(stripped) > MAX_CLAUSE_LENGTH:
                raise ValueError(
                    f"Clause text must be {MAX_CLAUSE_LENGTH} characters or fewer."
                )
            cleaned.append(stripped)
        return cleaned


class BatchSummary(BaseModel):
    total_clauses: int
    attention_required: int
    safe: int
    privacy_attention: int
    payment_attention: int
    user_rights_attention: int


class BatchPredictResponse(BaseModel):
    results: List[PredictResponse]
    summary: BatchSummary


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool


class ModelInfoResponse(BaseModel):
    encoder_name: str
    class_names: List[str]
    dataset_size: int
    training_timestamp: str
    test_accuracy: float


class RealsitePage(BaseModel):
    source_url: str
    clauses: List[str]


class RealsiteCacheResponse(BaseModel):
    domain: str
    site_name: str
    fetched_at: str
    pages: Dict[str, RealsitePage]


class RealsiteCacheListResponse(BaseModel):
    domains: Dict[str, str]


class BuildRealsiteRequest(BaseModel):
    domain: str = Field(..., description="Domain as it appears in the address bar, e.g. example.com")
    site_name: str = Field(..., description="Display name, e.g. Example Inc.")
    terms_url: str | None = Field(None, description="Terms of Service URL")
    privacy_url: str | None = Field(None, description="Privacy Policy URL")

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Domain must not be empty.")
        return cleaned

    @field_validator("site_name")
    @classmethod
    def validate_site_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Site name must not be empty.")
        return cleaned


class BuildRealsitePageResult(BaseModel):
    source_url: str
    clause_count: int | None = None
    seconds: float | None = None
    error: str | None = None


class BuildRealsiteResponse(BaseModel):
    domain: str
    site_name: str
    cached: bool
    pages: Dict[str, BuildRealsitePageResult]
