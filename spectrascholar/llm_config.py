"""Resolve an OpenAI-compatible chat endpoint from environment variables.

DeepSeek exposes an OpenAI-compatible chat API but uses a different key name
(``DEEPSEEK_API_KEY``) and base URL.  The project's own extraction/answer code
uses the OpenAI SDK, so this module lets it share one credential resolver.
Embeddings are intentionally separate: DeepSeek does not provide an embedding
endpoint, so ``EMBEDDING_BACKEND`` stays ``hash`` unless another provider is
configured.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class LLMConfigurationError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code = "missing_api_key"


@dataclass(frozen=True)
class LLMCredentials:
    provider: str
    api_key: str
    base_url: str | None


def resolve_llm_credentials(*, required: bool = True) -> LLMCredentials | None:
    """Prefer explicit OpenAI settings, then fall back to DeepSeek.

    ``OPENAI_BASE_URL`` is honoured only for the OpenAI/OpenAI-compatible path.
    A DeepSeek key is used with the official OpenAI-compatible base URL.
    """
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key:
        return LLMCredentials(
            provider="openai",
            api_key=openai_key,
            base_url=os.getenv("OPENAI_BASE_URL", "").strip() or None,
        )
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if deepseek_key:
        return LLMCredentials(
            provider="deepseek",
            api_key=deepseek_key,
            base_url=DEEPSEEK_BASE_URL,
        )
    if required:
        raise LLMConfigurationError(
            "缺少聊天模型密钥：请配置 OPENAI_API_KEY，或 DEEPSEEK_API_KEY。"
            "DeepSeek 没有 embedding API，语义检索仍需其他 embedding 服务；"
            "离线模式可用 EMBEDDING_BACKEND=hash。"
        )
    return None
