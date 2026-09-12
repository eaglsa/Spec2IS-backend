"""
pipeline/explain.py — Step 6

explain_candidates(candidates, spec_summary) -> list[dict]

Calls the LLM ONCE with all validated candidates and fills in the 'why' field.
If the LLM call fails we fall back to a template string so the API never breaks.
"""
from __future__ import annotations

import logging

import llm_client

logger = logging.getLogger(__name__)


def explain_candidates(
    candidates: list[dict],
    spec_summary: str = "",
) -> list[dict]:
    """
    Step 6 of the pipeline.

    Parameters
    ----------
    candidates : validated candidate dicts from validate.py
    spec_summary : short text representing the original spec (used in prompt)

    Returns
    -------
    Same list with 'why' field populated for each candidate.
    """
    if not candidates:
        return candidates

    # Only explain the top-N to keep the prompt size manageable
    MAX_EXPLAIN = 10
    to_explain = candidates[:MAX_EXPLAIN]

    try:
        why_map: dict = llm_client.explain(to_explain, spec_summary=spec_summary)
    except Exception as exc:
        logger.error("explain_candidates: LLM call failed: %s", exc)
        why_map = {}

    for c in candidates:
        snum = c["standard_number"]
        c["why"] = why_map.get(snum) or (
            f"{snum} – {c.get('title', '')} is relevant to the specification "
            f"(domain: {c.get('domain', 'N/A')})."
        )

    return candidates
