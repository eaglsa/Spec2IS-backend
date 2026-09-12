"""
Pydantic v2 request/response models for the /analyze endpoint.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    specification_text: str = Field(
        ...,
        min_length=10,
        description="Raw engineering specification text to analyse.",
    )


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class Recommendation(BaseModel):
    standard_number: str
    version_year: str | None = None
    status: Literal["current", "superseded", "withdrawn"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    action: Literal["recommended", "verify_replacement", "manual_verification"]
    why: str
    replacement_standard: str | None = None
    ambiguous: bool = False
    ambiguity_reason: str | None = None


class AnalyzeResponse(BaseModel):
    specification: str
    recommendations: list[Recommendation]
    areas_to_verify: list[str] = Field(
        default_factory=list,
        description=(
            "Domains / product areas where no candidate cleared the "
            "confidence threshold."
        ),
    )
