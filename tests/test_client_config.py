import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def _reload_client():
    import llm_ads_repro.client as c

    importlib.reload(c)
    return c


@pytest.fixture(autouse=True)
def clear_llm_env(monkeypatch):
    for k in list(os.environ):
        if k in ("OPENAI_API_KEY", "LLMAPI_KEY", "OPENAI_BASE_URL", "LLM_BASE_URL"):
            monkeypatch.delenv(k, raising=False)


def test_default_rrze_base_when_only_llmapi_key(monkeypatch):
    monkeypatch.setenv("LLMAPI_KEY", "sk-test")
    c = _reload_client()
    assert c.resolve_base_url() == c.DEFAULT_NHR_FAU_LLM_BASE


def test_no_default_base_when_openai_key_only(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    c = _reload_client()
    assert c.resolve_base_url() is None


def test_explicit_base_wins(monkeypatch):
    monkeypatch.setenv("LLMAPI_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.com/v1")
    c = _reload_client()
    assert c.resolve_base_url() == "https://example.com/v1"


def test_llmapi_key_used_when_openai_unset(monkeypatch):
    monkeypatch.setenv("LLMAPI_KEY", "sk-rrze")
    c = _reload_client()
    assert c.resolve_api_key() == "sk-rrze"


def test_openai_key_preferred_when_both_set(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("LLMAPI_KEY", "sk-rrze")
    c = _reload_client()
    assert c.resolve_api_key() == "sk-openai"


def test_llm_base_url_alias(monkeypatch):
    monkeypatch.setenv("LLMAPI_KEY", "sk-test")
    monkeypatch.setenv("LLM_BASE_URL", "https://custom.example/v1")
    c = _reload_client()
    assert c.resolve_base_url() == "https://custom.example/v1"
