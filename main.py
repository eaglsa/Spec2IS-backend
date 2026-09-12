"""
main.py — FastAPI application entry point.

Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

load_dotenv()

from db.session import get_db
from pipeline.explain import explain_candidates
from pipeline.extract import extract_requirements
from pipeline.retrieve import keyword_search, merge_and_score, vector_search
from pipeline.validate import CONFIDENCE_THRESHOLD, validate
from schemas import AnalyzeRequest, AnalyzeResponse, Recommendation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Spec2IS — IS Recommendation Engine",
    description=(
        "Prototype API for SIH 2026 PS 26108. "
        "POST a specification text and receive relevant Indian Standards (IS)."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict:
    return {
        "message": "Welcome to Spec2IS — IS Recommendation Engine API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    body: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    """
    Main endpoint.  Runs the full 6-step pipeline:
      1. extract requirements  (LLM)
      2. keyword search        (Postgres ILIKE)
      3. vector search         (pgvector cosine)
      4. merge & score         (pure Python)
      5. validate              (pure Python, DB lookups)
      6. explain               (LLM, single call)
    """
    spec_text = body.specification_text
    logger.info("/analyze request: %d chars", len(spec_text))

    # ------------------------------------------------------------------
    # Step 1 — Extract
    # ------------------------------------------------------------------
    try:
        requirements = extract_requirements(spec_text)
    except Exception as exc:
        logger.exception("extract_requirements failed")
        raise HTTPException(status_code=502, detail=f"LLM extraction failed: {exc}")

    extracted_domains: list[str] = requirements.get("domains", [])

    # ------------------------------------------------------------------
    # Steps 2 & 3 — Retrieve
    # ------------------------------------------------------------------
    keyword_ids = await keyword_search(db, requirements)
    vector_hits = await vector_search(db, requirements)

    # ------------------------------------------------------------------
    # Step 4 — Merge
    # ------------------------------------------------------------------
    scored_candidates = merge_and_score(keyword_ids, vector_hits)

    # ------------------------------------------------------------------
    # Step 5 — Validate
    # ------------------------------------------------------------------
    validated = await validate(db, scored_candidates)

    # ------------------------------------------------------------------
    # Step 6 — Explain (single LLM call for top candidates only)
    # ------------------------------------------------------------------
    spec_summary = spec_text[:300]
    validated = explain_candidates(validated, spec_summary=spec_summary)

    # ------------------------------------------------------------------
    # Step 7 — Assemble response; handle zero-confidence case
    # ------------------------------------------------------------------
    above_threshold = [v for v in validated if v["confidence"] >= CONFIDENCE_THRESHOLD]

    areas_to_verify: list[str] = []
    if not above_threshold:
        # No confident matches — surface all extracted domains as areas to verify
        areas_to_verify = extracted_domains or ["General / Unclassified"]
        logger.info(
            "/analyze: no candidates above threshold %.2f — returning areas_to_verify",
            CONFIDENCE_THRESHOLD,
        )

    recommendations = [
        Recommendation(
            standard_number=v["standard_number"],
            version_year=v["version_year"],
            status=v["status"],  # type: ignore[arg-type]
            confidence=v["confidence"],
            action=v["action"],  # type: ignore[arg-type]
            why=v["why"],
            replacement_standard=v["replacement_standard"],
            ambiguous=v["ambiguous"],
            ambiguity_reason=v["ambiguity_reason"],
        )
        for v in above_threshold
    ]

    return AnalyzeResponse(
        specification=spec_text,
        recommendations=recommendations,
        areas_to_verify=areas_to_verify,
    )
