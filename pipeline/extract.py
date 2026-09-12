"""
pipeline/extract.py — Step 1

extract_requirements(text) -> dict

Calls the LLM to parse raw specification text into structured fields:
  products, materials, applications, domains, parameters, keywords
"""
from __future__ import annotations

import logging

from llm_client import extract as llm_extract

logger = logging.getLogger(__name__)

# Fields we expect from the LLM; used for safe defaults
_EXPECTED_KEYS = ("products", "materials", "applications", "domains", "parameters", "keywords")


def extract_requirements(text: str) -> dict:
    """
    Step 1 of the pipeline.

    Parameters
    ----------
    text : str
        Raw engineering specification text.

    Returns
    -------
    dict with keys:
        products      list[str]
        materials     list[str]
        applications  list[str]
        domains       list[str]
        parameters    dict[str, str]   {name: "value unit"}
        keywords      list[str]
    """
    logger.info("extract_requirements: calling LLM (%d chars)", len(text))
    try:
        result = llm_extract(text)
    except Exception as exc:
        logger.error("LLM extraction failed: %s", exc)
        raise

    # Normalise — guarantee expected keys exist even if LLM omits them
    for key in _EXPECTED_KEYS:
        if key not in result:
            result[key] = {} if key == "parameters" else []

    logger.info(
        "extract_requirements: domains=%s keywords=%s",
        result.get("domains"),
        result.get("keywords"),
    )
    return result
