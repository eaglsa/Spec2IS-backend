"""
LLM client — supports Gemini (google-generativeai) and Anthropic (anthropic).
Provider is selected via LLM_PROVIDER env var.  Both return strict JSON; any
prose wrapper from the model is stripped before parsing.

Public API
----------
extract(text: str) -> dict
    Ask the LLM to extract structured requirements from a specification.

explain(candidates: list[dict]) -> dict
    Ask the LLM to produce a "why" string for each candidate standard in one
    round-trip.  Returns {standard_number: why_string, ...}.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers that some models add despite instructions."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_json(raw: str) -> Any:
    return json.loads(_strip_markdown_fences(raw))


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------

def _gemini_call(prompt: str) -> str:
    import time
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore

    api_key = os.environ["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)

    models_to_try = [GEMINI_MODEL, "gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
    # Preserve order without duplicates
    models_to_try = list(dict.fromkeys(models_to_try))

    last_exc = None
    for model_name in models_to_try:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.0,
                    ),
                )
                return response.text
            except Exception as exc:
                last_exc = exc
                err_str = str(exc)
                if "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str or "429" in err_str:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                else:
                    break

    assert last_exc is not None
    raise last_exc


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

def _anthropic_call(prompt: str) -> str:
    import anthropic  # type: ignore

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def _call_llm(prompt: str) -> str:
    if LLM_PROVIDER == "gemini":
        return _gemini_call(prompt)
    elif LLM_PROVIDER == "anthropic":
        return _anthropic_call(prompt)
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER!r}")


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

_EXTRACT_PROMPT = """You are an expert in Indian engineering standards (BIS/IS).
Given the engineering specification text below, extract structured requirements.

Return ONLY a valid JSON object with these keys (omit any key if not found):
{{
  "products": ["list of product types / items mentioned"],
  "materials": ["list of materials mentioned"],
  "applications": ["list of application areas"],
  "domains": ["list of engineering domains, e.g. civil, electrical, mechanical"],
  "parameters": {{
    "parameter_name": "value with unit"
  }},
  "keywords": ["important technical keywords for IS standard search"]
}}

Specification text:
---
{text}
---

Output JSON only. No prose, no explanation, no markdown fences."""


def extract(text: str) -> dict:
    """Step 1 — extract structured requirements from raw specification text."""
    prompt = _EXTRACT_PROMPT.format(text=text)
    raw = _call_llm(prompt)
    return _parse_json(raw)


_EXPLAIN_PROMPT = """You are an expert in Indian Standards (BIS/IS).
Below is a list of candidate IS standards retrieved from a database for an engineering
specification. For each standard, write a concise 1–2 sentence explanation of WHY it
is relevant to the given specification.

CRITICAL RULES:
- Only reference IS standards that appear in the provided candidate list.
- Do NOT invent, guess, or mention any IS number not present in the list below.
- Keep each explanation factual and under 40 words.

Specification summary: {spec_summary}

Candidate standards (JSON):
{candidates_json}

Return ONLY a JSON object mapping each standard_number to its explanation:
{{
  "IS_NUMBER": "why this standard is relevant...",
  ...
}}

Output JSON only. No prose, no markdown fences."""


def explain(candidates: list[dict], spec_summary: str = "") -> dict:
    """Step 6 — generate 'why' strings for validated candidates in one LLM call."""
    if not candidates:
        return {}
    candidates_json = json.dumps(
        [
            {
                "standard_number": c.get("standard_number"),
                "title": c.get("title"),
                "description": c.get("description", ""),
                "domain": c.get("domain", ""),
                "status": c.get("status", ""),
            }
            for c in candidates
        ],
        indent=2,
    )
    prompt = _EXPLAIN_PROMPT.format(
        spec_summary=spec_summary[:500],
        candidates_json=candidates_json,
    )
    raw = _call_llm(prompt)
    result = _parse_json(raw)
    # Ensure all keys are present; default to empty string on parse error
    return {str(k): str(v) for k, v in result.items()}
