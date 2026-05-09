"""OpenAI-compatible API client for running trials."""

from __future__ import annotations

import os
from typing import Optional

from openai import OpenAI


def get_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set OPENAI_API_KEY in the environment (or a .env file loaded by scripts)."
        )
    base_url = os.environ.get("OPENAI_BASE_URL")
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


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
