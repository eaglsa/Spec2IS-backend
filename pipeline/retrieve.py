"""
pipeline/retrieve.py — Steps 2, 3, 4

keyword_search(db, requirements) -> list[int]   (standard_ids)
vector_search(db, requirements)  -> list[dict]  ({standard_id, score})
merge_and_score(keyword_ids, vector_hits) -> list[dict] ranked by combined score
"""
from __future__ import annotations

import logging
import os
from typing import Any

from sentence_transformers import SentenceTransformer  # type: ignore
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Standard, StandardEmbedding, StandardKeyword, StandardKeywordMap

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

EMBEDDING_MODEL_NAME: str = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
VECTOR_WEIGHT: float = float(os.getenv("VECTOR_WEIGHT", "0.7"))
KEYWORD_WEIGHT: float = float(os.getenv("KEYWORD_WEIGHT", "0.3"))
MAX_CANDIDATES: int = int(os.getenv("MAX_CANDIDATES", "20"))

# Lazy-loaded singleton — avoids loading the model at import time in tests
_encoder: SentenceTransformer | None = None


def _get_encoder() -> SentenceTransformer:
    global _encoder
    if _encoder is None:
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL_NAME)
        _encoder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _encoder


def _requirements_to_query_string(requirements: dict) -> str:
    """Flatten requirements dict into a single query string for embedding."""
    parts: list[str] = []
    parts.extend(requirements.get("products", []))
    parts.extend(requirements.get("materials", []))
    parts.extend(requirements.get("applications", []))
    parts.extend(requirements.get("domains", []))
    parts.extend(requirements.get("keywords", []))
    for k, v in requirements.get("parameters", {}).items():
        parts.append(f"{k} {v}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Step 2 — Keyword search
# ---------------------------------------------------------------------------


async def keyword_search(db: AsyncSession, requirements: dict) -> list[int]:
    """
    Return a list of standard_ids that match any extracted keyword,
    product, material, or application via ILIKE.

    Uses standard_keywords + standard_keyword_map tables.
    """
    # Build a list of search terms
    terms: list[str] = []
    terms.extend(requirements.get("keywords", []))
    terms.extend(requirements.get("products", []))
    terms.extend(requirements.get("materials", []))
    terms.extend(requirements.get("applications", []))
    terms.extend(requirements.get("domains", []))

    if not terms:
        return []

    # Also search standard titles / descriptions directly
    ilike_conditions = " OR ".join(
        [f"s.title ILIKE :term{i} OR s.description ILIKE :term{i}" for i in range(len(terms))]
    )
    keyword_ilike = " OR ".join(
        [f"sk.keyword ILIKE :term{i}" for i in range(len(terms))]
    )

    params: dict[str, str] = {f"term{i}": f"%{t}%" for i, t in enumerate(terms)}

    sql = text(
        f"""
        SELECT DISTINCT s.id
        FROM standards s
        LEFT JOIN standard_keyword_map skm ON skm.standard_id = s.id
        LEFT JOIN standard_keywords sk ON sk.id = skm.keyword_id
        WHERE {ilike_conditions} OR {keyword_ilike}
        LIMIT :limit
        """
    )
    params["limit"] = MAX_CANDIDATES * 2  # type: ignore[assignment]

    result = await db.execute(sql, params)
    rows = result.fetchall()
    ids = [row[0] for row in rows]
    logger.info("keyword_search: found %d candidate standard_ids", len(ids))
    return ids


# ---------------------------------------------------------------------------
# Step 3 — Vector search
# ---------------------------------------------------------------------------


async def vector_search(db: AsyncSession, requirements: dict) -> list[dict]:
    """
    Embed the requirements and run cosine similarity search against
    standard_embeddings using pgvector.

    Returns list of {standard_id, score} dicts, sorted by score desc.
    """
    query_str = _requirements_to_query_string(requirements)
    if not query_str.strip():
        return []

    encoder = _get_encoder()
    query_vec = encoder.encode(query_str, normalize_embeddings=True).tolist()

    # pgvector cosine distance: 1 - (a <=> b)  gives cosine similarity
    sql = text(
        """
        SELECT standard_id,
               1 - (embedding <=> CAST(:vec AS vector)) AS score
        FROM standard_embeddings
        ORDER BY embedding <=> CAST(:vec AS vector)
        LIMIT :limit
        """
    )
    vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"
    result = await db.execute(sql, {"vec": vec_str, "limit": MAX_CANDIDATES})
    rows = result.fetchall()
    hits = [{"standard_id": row[0], "score": float(row[1])} for row in rows]
    logger.info("vector_search: found %d hits (top score=%.3f)", len(hits), hits[0]["score"] if hits else 0)
    return hits


# ---------------------------------------------------------------------------
# Step 4 — Merge and score
# ---------------------------------------------------------------------------


def merge_and_score(
    keyword_ids: list[int],
    vector_hits: list[dict],
) -> list[dict]:
    """
    Combine keyword and vector results into a single ranked list.

    Scoring:
        combined = VECTOR_WEIGHT * vector_score + KEYWORD_WEIGHT * keyword_boost

    keyword_boost = 1.0 if the standard_id appears in keyword results, else 0.
    Returns list of {standard_id, combined_score, vector_score, keyword_hit},
    sorted by combined_score descending.
    """
    keyword_set = set(keyword_ids)

    scored: dict[int, dict] = {}

    for hit in vector_hits:
        sid = hit["standard_id"]
        v_score = hit["score"]
        k_boost = 1.0 if sid in keyword_set else 0.0
        combined = VECTOR_WEIGHT * v_score + KEYWORD_WEIGHT * k_boost
        scored[sid] = {
            "standard_id": sid,
            "vector_score": v_score,
            "keyword_hit": sid in keyword_set,
            "combined_score": combined,
        }

    # Include keyword-only hits that the vector search missed
    for sid in keyword_set:
        if sid not in scored:
            scored[sid] = {
                "standard_id": sid,
                "vector_score": 0.0,
                "keyword_hit": True,
                "combined_score": KEYWORD_WEIGHT * 1.0,
            }

    ranked = sorted(scored.values(), key=lambda x: x["combined_score"], reverse=True)
    top = ranked[:MAX_CANDIDATES]
    logger.info(
        "merge_and_score: %d merged candidates (top combined=%.3f)",
        len(top),
        top[0]["combined_score"] if top else 0,
    )
    return top
