"""
Groq client wrapper with retry logic and structured JSON extraction.

Retry strategy:
  - Per-minute token/request rate limit (429): sleep the server-suggested delay, then retry.
  - Other transient errors: exponential backoff up to 60 s.
"""
import json
import logging
import re
import time
from typing import Any

from groq import Groq, RateLimitError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from core.config import settings

logger = logging.getLogger(__name__)

_client = Groq(api_key=settings.groq_api_key)


# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------

def _is_rate_limit(exc: Exception) -> bool:
    return isinstance(exc, RateLimitError)


def _should_retry(exc: Exception) -> bool:
    return _is_rate_limit(exc) or not isinstance(exc, (ValueError, TypeError))


def _extract_retry_after(exc: Exception) -> float | None:
    """Parse the server-suggested wait time from the error message if present."""
    match = re.search(r"try again in\s+(\d+(?:\.\d+)?)s", str(exc), re.IGNORECASE)
    return float(match.group(1)) if match else None


# ---------------------------------------------------------------------------
# Core LLM call
# ---------------------------------------------------------------------------

@retry(
    retry=retry_if_exception(_should_retry),
    stop=stop_after_attempt(settings.max_retries),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    reraise=True,
)
def call_llm(prompt: str) -> str:
    """Send a prompt to Groq and return the raw text response."""
    logger.debug("LLM call — prompt length: %d chars", len(prompt))
    try:
        response = _client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=8192,
        )
    except RateLimitError as exc:
        delay = _extract_retry_after(exc) or 30.0
        logger.warning("Rate limit hit — sleeping %.0fs before retry.", delay)
        time.sleep(delay)
        raise
    text = response.choices[0].message.content.strip()
    logger.debug("LLM response — length: %d chars", len(text))
    return text


# ---------------------------------------------------------------------------
# JSON-typed call
# ---------------------------------------------------------------------------

def call_llm_json(prompt: str) -> Any:
    """
    Call the LLM and parse the response as JSON.
    Strips markdown code fences if present before parsing.
    Falls back to regex block extraction on decode failure.
    Raises ValueError if the response cannot be decoded at all.
    """
    raw = call_llm(prompt)
    cleaned = _strip_code_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse failed, attempting regex extraction. Error: %s", exc)
        extracted = _extract_json_block(raw)
        if extracted:
            return json.loads(extracted)
        raise ValueError(f"LLM did not return valid JSON.\nRaw response:\n{raw}") from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json_block(text: str) -> str | None:
    match = re.search(r"(\{[\s\S]+\}|\[[\s\S]+\])", text)
    return match.group(0) if match else None
