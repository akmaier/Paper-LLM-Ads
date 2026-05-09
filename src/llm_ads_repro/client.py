"""OpenAI-compatible API client for running trials."""

from __future__ import annotations

import os
from typing import Optional

from openai import OpenAI

# NHR@FAU / RRZE OpenAI-compatible gateway (see https://hpc.fau.de/request-llm-api-key/)
DEFAULT_NHR_FAU_LLM_BASE = "https://hub.nhr.fau.de/api/llmgw/v1"


def resolve_api_key() -> str:
    return (os.environ.get("OPENAI_API_KEY") or os.environ.get("LLMAPI_KEY") or "").strip()


def resolve_base_url() -> Optional[str]:
    """
    Base URL for OpenAI-compatible APIs.

    Precedence: OPENAI_BASE_URL, then LLM_BASE_URL, else if LLMAPI_KEY is set
    default to the NHR@FAU gateway (RRZE docs).
    """
    explicit = (os.environ.get("OPENAI_BASE_URL") or os.environ.get("LLM_BASE_URL") or "").strip()
    if explicit:
        return explicit
    llmapi = (os.environ.get("LLMAPI_KEY") or "").strip()
    openai = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if llmapi and not openai:
        return DEFAULT_NHR_FAU_LLM_BASE
    return None


def get_client() -> OpenAI:
    api_key = resolve_api_key()
    if not api_key:
        raise RuntimeError(
            "Set OPENAI_API_KEY or LLMAPI_KEY in the environment (or a .env file loaded by scripts)."
        )
    base_url = resolve_base_url()
    kwargs: dict = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def list_chat_model_ids(client: OpenAI) -> list[str]:
    """Return sorted unique model ids from GET /v1/models (OpenAI-compatible)."""
    resp = client.models.list()
    data = getattr(resp, "data", None) or []
    ids: list[str] = []
    for m in data:
        mid = getattr(m, "id", None)
        if mid:
            ids.append(mid)
    return sorted(set(ids))


def complete_chat(
    client: OpenAI,
    model: str,
    system: str,
    user: str,
    *,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    reasoning_effort: Optional[str] = None,
) -> str:
    """Completion for chat models; optional reasoning_effort for o-series / GPT-5 style APIs."""
    extra: dict = {}
    if reasoning_effort:
        extra["reasoning_effort"] = reasoning_effort

    # Some servers use max_completion_tokens instead of max_tokens
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            **extra,
        )
    except TypeError:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_completion_tokens=max_tokens,
            temperature=temperature,
        )
    choice = resp.choices[0]
    msg = choice.message
    content = getattr(msg, "content", None) or ""
    return content.strip()
