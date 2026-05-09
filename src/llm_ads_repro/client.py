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
    max_tokens: int = 4096,
    temperature: float = 0.7,
    reasoning_effort: Optional[str] = None,
) -> str:
    """Completion for chat models; optional reasoning_effort for o-series / GPT-5 style APIs.

    Falls back to `message.reasoning` / `message.reasoning_content` when
    `message.content` is empty. The NHR@FAU gateway exposes some reasoning
    models (e.g. Magistral) that route the user-facing answer into
    `reasoning` and leave `content` blank; we treat both as the assistant's
    output text for the purposes of judging.
    """
    extra: dict = {}
    if reasoning_effort:
        extra["reasoning_effort"] = reasoning_effort

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    # Some servers cap total context (input + output) at a small budget. If
    # max_tokens exceeds (context_window - input_tokens) we get a 400 with
    # "ContextWindowExceededError"; halve max_tokens and retry until small
    # enough. Some servers also use max_completion_tokens instead of max_tokens.
    cur = max_tokens
    last_err: Optional[Exception] = None
    while cur >= 64:
        try:
            try:
                resp = client.chat.completions.create(
                    model=model, messages=messages,
                    max_tokens=cur, temperature=temperature, **extra,
                )
            except TypeError:
                resp = client.chat.completions.create(
                    model=model, messages=messages,
                    max_completion_tokens=cur, temperature=temperature,
                )
            break
        except Exception as e:
            s = str(e)
            if "ContextWindowExceeded" in s or "max_tokens" in s and "too large" in s:
                last_err = e
                cur = cur // 2
                continue
            raise
    else:
        raise last_err if last_err else RuntimeError("max_tokens shrink loop exited")
    msg = resp.choices[0].message
    content = (getattr(msg, "content", None) or "").strip()
    if content:
        return content
    rc = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None)
    return (rc or "").strip()
