from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import spectrascholar.extraction.llm as llm_module
from spectrascholar.extraction.llm import extract_llm
from spectrascholar.llm_config import (
    DEEPSEEK_BASE_URL,
    LLMConfigurationError,
    resolve_llm_credentials,
)


def test_credentials_require_a_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(LLMConfigurationError):
        resolve_llm_credentials()
    assert resolve_llm_credentials(required=False) is None


def test_deepseek_key_is_used_when_openai_is_absent(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-test-key")
    credentials = resolve_llm_credentials()
    assert credentials is not None
    assert credentials.provider == "deepseek"
    assert credentials.base_url == DEEPSEEK_BASE_URL
    assert credentials.api_key == "deepseek-test-key"


def test_openai_key_wins_when_both_are_configured(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-test-key")
    credentials = resolve_llm_credentials()
    assert credentials is not None
    assert credentials.provider == "openai"
    assert credentials.api_key == "openai-test-key"
    assert credentials.base_url == "https://example.invalid/v1"


class _FakeCompletions:
    async def create(self, **kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))])


class _FakeClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=_FakeCompletions())


def test_extraction_client_uses_deepseek_base_url(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-test-key")
    captured = {}

    def factory(**kwargs):
        captured.update(kwargs)
        return _FakeClient()

    monkeypatch.setattr(llm_module, "AsyncOpenAI", factory)
    paper = asyncio.run(extract_llm("doc", "x.pdf", ["Title page text"]))
    assert captured["api_key"] == "deepseek-test-key"
    assert captured["base_url"] == DEEPSEEK_BASE_URL
    assert paper.metrics == []
