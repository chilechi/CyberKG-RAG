import hashlib
import math

import httpx

from app.core.config import Settings


def mock_embedding(text: str, dim: int) -> list[float]:
    """生成确定性 mock 向量，保证没有 API Key 时系统链路仍可运行。"""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < dim:
        for byte in digest:
            values.append((byte / 255.0) * 2.0 - 1.0)
            if len(values) == dim:
                break
        digest = hashlib.sha256(digest).digest()

    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


def dashscope_embedding(settings: Settings, text: str) -> list[float]:
    """调用阿里云百炼 DashScope 文本向量 API。"""
    if not settings.dashscope_api_key:
        raise ValueError("DASHSCOPE_API_KEY is required when EMBEDDING_PROVIDER=dashscope")

    response = httpx.post(
        settings.dashscope_embedding_url,
        headers={
            "Authorization": f"Bearer {settings.dashscope_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.embedding_model,
            "input": {
                "texts": [text],
            },
            "parameters": {
                "dimension": settings.embedding_dim,
            },
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    try:
        embedding = payload["output"]["embeddings"][0]["embedding"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"Unexpected DashScope embedding response: {payload}") from exc
    return [float(value) for value in embedding]


def embed_text(settings: Settings, text: str) -> list[float]:
    """根据配置选择 mock 或 DashScope embedding provider。"""
    provider = settings.embedding_provider.lower()
    if provider == "mock":
        return mock_embedding(text, settings.embedding_dim)
    if provider == "dashscope":
        return dashscope_embedding(settings, text)
    raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")
