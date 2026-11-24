"""ClauseGuard FastAPI backend.

Educational prototype. Not legal advice. All inference runs locally using a
MiniLM sentence encoder and a student-trained LogisticRegression classifier.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .model_service import ModelNotLoadedError, model_service
from .realsite_builder import PlaywrightUnavailableError, add_and_build_site
from .realsite_cache import realsite_cache
from .schemas import (
    BatchPredictRequest,
    BatchPredictResponse,
    BatchSummary,
    BuildRealsiteRequest,
    BuildRealsiteResponse,
    HealthResponse,
    ModelInfoResponse,
    PredictRequest,
    PredictResponse,
    RealsiteCacheListResponse,
    RealsiteCacheResponse,
)

app = FastAPI(
    title="ClauseGuard",
    description=(
        "Educational prototype API that classifies synthetic-style Terms and "
        "Conditions clauses into cautious attention categories. Not legal advice."
    ),
    version="1.0.0",
)

# The demo websites and browser extension run on the host machine, so CORS
# must allow the local demo origins plus extension-origin requests.
ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"^chrome-extension://.*$|^moz-extension://.*$|^edge-extension://.*$",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="healthy", model_loaded=model_service.is_loaded)


@app.get("/model-info", response_model=ModelInfoResponse)
def model_info() -> ModelInfoResponse:
    try:
        metadata = model_service.metadata
    except ModelNotLoadedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ModelInfoResponse(
        encoder_name=metadata["encoder_name"],
        class_names=metadata["class_names"],
        dataset_size=metadata["dataset_size"],
        training_timestamp=metadata["training_timestamp"],
        test_accuracy=metadata["test_accuracy"],
    )


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    try:
        result = model_service.classify_one(request.text)
    except ModelNotLoadedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return PredictResponse(**result)


@app.post("/predict-batch", response_model=BatchPredictResponse)
def predict_batch(request: BatchPredictRequest) -> BatchPredictResponse:
    try:
        results = model_service.classify_batch(request.clauses)
    except ModelNotLoadedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    summary = model_service.build_summary(results)
    return BatchPredictResponse(
        results=[PredictResponse(**r) for r in results],
        summary=BatchSummary(**summary),
    )


@app.get("/realsite-cache", response_model=RealsiteCacheListResponse)
def list_realsite_cache() -> RealsiteCacheListResponse:
    """Lists domains that have a pre-built demo cache available."""
    return RealsiteCacheListResponse(domains=realsite_cache.list_domains())


@app.get("/realsite-cache/{domain}", response_model=RealsiteCacheResponse)
def get_realsite_cache(domain: str) -> RealsiteCacheResponse:
    """Returns pre-extracted clause text for a cached real-world domain.

    Only raw clause text is cached - no predictions. The extension still
    classifies these clauses live via /predict-batch using whatever model
    is currently trained, so results always reflect the current model.
    """
    entry = realsite_cache.get(domain)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"No demo cache for domain '{domain}'.")

    return RealsiteCacheResponse(
        domain=domain,
        site_name=entry["site_name"],
        fetched_at=entry["fetched_at"],
        pages=entry["pages"],
    )


@app.post("/realsite-cache/build", response_model=BuildRealsiteResponse)
async def build_realsite_cache(request: BuildRealsiteRequest) -> BuildRealsiteResponse:
    """Adds a new site to the real-site demo cache (used by the novice-
    friendly admin HTML form at demo/admin-add-site.html, and equivalent to
    running `build_realsite_cache.py --add` on the command line).

    This renders the provided URL(s) with a real headless browser, so it
    can take roughly 5-20 seconds. It never runs predictions - only raw
    clause text is cached, so results always reflect whatever model is
    currently trained.
    """
    if not request.terms_url and not request.privacy_url:
        raise HTTPException(
            status_code=422, detail="Provide at least one of terms_url or privacy_url."
        )

    try:
        # Playwright renders synchronously; run it off the event loop so
        # this single admin action doesn't block /health, /predict, etc.
        result = await run_in_threadpool(
            add_and_build_site,
            request.domain,
            request.site_name,
            request.terms_url,
            request.privacy_url,
        )
    except PlaywrightUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return BuildRealsiteResponse(**result)
