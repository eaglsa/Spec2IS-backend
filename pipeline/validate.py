"""
pipeline/validate.py — Step 5

validate(db, candidates) -> list[dict]

Deterministic checks (no LLM):
  - Fetch full standard + latest version from DB
  - Check status; if superseded/withdrawn, look up replacement via standard_relationships
  - Detect ambiguity when a standard has multiple parts
  - Apply CONFIDENCE_THRESHOLD to decide action field
"""
from __future__ import annotations

import logging
import os
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    Standard,
    StandardDomain,
    StandardPart,
    StandardRelationship,
    StandardVersion,
)

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.45"))

# status values as they appear in the DB (case-insensitive comparison used below)
_CURRENT = "current"
_SUPERSEDED = "superseded"
_WITHDRAWN = "withdrawn"

_REPLACEMENT_REL_TYPES = {"REVISES", "SUPERSEDES", "REVISED_BY", "SUPERSEDED_BY", "WITHDRAWN"}


async def _get_replacement_standard_number(
    db: AsyncSession, standard_id: int, version_id: int | None
) -> str | None:
    """
    Look up standard_relationships for a replacement link where this
    standard is the *source* (i.e. the old one), and return the target's
    standard_number or target_standard_number_raw.
    """
    stmt = select(StandardRelationship).where(
        StandardRelationship.source_standard_id == standard_id,
        StandardRelationship.relationship_type.in_(list(_REPLACEMENT_REL_TYPES)),
    )
    result = await db.execute(stmt)
    rel = result.scalars().first()
    if rel is None:
        return None

    # First attempt to resolve via target standard FK if available
    if rel.target_standard_id is not None:
        target = await db.get(Standard, rel.target_standard_id)
        if target and target.standard_number:
            return target.standard_number

    # Fallback to raw string reference if target standard is external/un-ingested
    return rel.target_standard_number_raw


async def validate(
    db: AsyncSession,
    candidates: list[dict],
) -> list[dict]:
    """
    Enrich and validate each scored candidate.

    Parameters
    ----------
    db : AsyncSession
    candidates : list of dicts from merge_and_score, each having
                 {standard_id, combined_score, vector_score, keyword_hit}

    Returns
    -------
    list of enriched dicts ready for the explain step and response assembly.
    """
    validated: list[dict] = []

    for c in candidates:
        sid: int = c["standard_id"]
        score: float = c["combined_score"]

        # ---- Load standard ----
        standard = await db.get(Standard, sid)
        if standard is None:
            logger.warning("validate: standard_id %d not found in DB, skipping", sid)
            continue

        # ---- Load domain name ----
        domain_name: str = ""
        if standard.domain_id:
            domain = await db.get(StandardDomain, standard.domain_id)
            domain_name = domain.name if domain else ""

        # ---- Load versions, pick latest ----
        versions_result = await db.execute(
            select(StandardVersion)
            .where(StandardVersion.standard_id == sid)
            .order_by(StandardVersion.year.desc().nullslast())
        )
        versions = versions_result.scalars().all()
        latest_version = versions[0] if versions else None

        raw_status: str = (
            (latest_version.status or "").lower() if latest_version else ""
        )

        # Normalise status
        if "supersede" in raw_status:
            norm_status = _SUPERSEDED
        elif "withdraw" in raw_status:
            norm_status = _WITHDRAWN
        else:
            norm_status = _CURRENT  # treat unknown as current (conservative)

        version_year: str | None = (
            str(latest_version.year) if latest_version and latest_version.year else None
        )
        version_id: int | None = latest_version.id if latest_version else None

        # ---- Replacement lookup ----
        replacement_standard: str | None = None
        if norm_status in (_SUPERSEDED, _WITHDRAWN):
            replacement_standard = await _get_replacement_standard_number(
                db, sid, version_id
            )

        # ---- Ambiguity check (multiple parts) ----
        ambiguous = False
        ambiguity_reason: str | None = None
        if latest_version:
            parts_result = await db.execute(
                select(StandardPart).where(
                    StandardPart.standard_version_id == latest_version.id
                )
            )
            parts = parts_result.scalars().all()
            if len(parts) > 1:
                ambiguous = True
                part_titles = ", ".join(
                    p.part_title or f"Part {p.part_number}" for p in parts
                )
                ambiguity_reason = (
                    f"Standard has {len(parts)} parts ({part_titles}). "
                    "Specify which part applies to your use case."
                )

        # ---- Determine action ----
        if score < CONFIDENCE_THRESHOLD:
            action = "manual_verification"
        elif norm_status in (_SUPERSEDED, _WITHDRAWN):
            action = "verify_replacement"
        else:
            action = "recommended"

        validated.append(
            {
                # identity
                "standard_id": sid,
                "standard_number": standard.standard_number,
                "title": standard.title,
                "description": standard.description or "",
                "domain": domain_name,
                # version
                "version_year": version_year,
                "version_id": version_id,
                # status
                "status": norm_status,
                "raw_status": raw_status,
                # scoring
                "confidence": round(min(score, 1.0), 4),
                # action
                "action": action,
                "replacement_standard": replacement_standard,
                # ambiguity
                "ambiguous": ambiguous,
                "ambiguity_reason": ambiguity_reason,
                # placeholder — filled by explain step
                "why": "",
            }
        )

    logger.info("validate: %d candidates after validation", len(validated))
    return validated
