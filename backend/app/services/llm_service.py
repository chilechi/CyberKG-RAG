import httpx

from app.core.config import Settings


SYSTEM_PROMPT = """你是网络安全知识图谱问答助手。
回答必须基于给定的图谱证据和文本证据，不要编造未出现在证据中的事实。
如果证据不足，要明确说明“当前证据不足”，并给出可以继续查询的方向。
回答使用简体中文，结构包括：结论、证据依据、防护建议。"""

FREE_LLM_SYSTEM_PROMPT = """你是网络安全问答助手。
回答使用简体中文，结构包括：结论、原理分析、防护建议。
如果问题缺少必要上下文，要说明不确定点。"""


def _format_graph_paths(graph_paths: list[list[str]]) -> str:
    if not graph_paths:
        return "无图谱路径。"
    return "\n".join(f"- {' -> '.join(path)}" for path in graph_paths[:12])


def _format_text_evidence(text_evidence) -> str:
    if not text_evidence:
        return "无文本证据。"
    lines = []
    for index, evidence in enumerate(text_evidence[:5], start=1):
        lines.append(
            f"{index}. 来源：{evidence.source}；实体：{evidence.entity_id}；"
            f"相关度：{evidence.score:.2f}；内容：{evidence.text}"
        )
    return "\n".join(lines)


def build_kg_rag_prompt(question: str, entity_id: str, graph_paths: list[list[str]], text_evidence) -> str:
    """把检索结果整理成 DeepSeek 可直接使用的证据提示词。"""
    return f"""用户问题：
{question}

识别到的核心实体：
{entity_id}

图谱证据：
{_format_graph_paths(graph_paths)}

文本证据：
{_format_text_evidence(text_evidence)}

请基于以上证据生成最终答案。"""


def generate_with_deepseek(settings: Settings, prompt: str) -> str | None:
    """调用 DeepSeek Chat Completions；未配置或调用失败时返回 None，由上层兜底。"""
    return _call_deepseek(settings, SYSTEM_PROMPT, prompt)


def _call_deepseek(settings: Settings, system_prompt: str, user_prompt: str) -> str | None:
    if not settings.deepseek_api_key.strip():
        return None

    url = settings.deepseek_base_url.rstrip("/") + "/chat/completions"
    try:
        response = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.deepseek_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.deepseek_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "stream": False,
            },
            timeout=settings.deepseek_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        answer = payload["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, TypeError):
        return None
    return answer.strip() or None


def generate_free_answer(settings: Settings, question: str) -> str | None:
    """普通 LLM 模式：不接检索证据，直接调用 DeepSeek 回答。"""
    return _call_deepseek(settings, FREE_LLM_SYSTEM_PROMPT, question)


def generate_rag_answer(settings: Settings, question: str, text_evidence) -> str | None:
    """普通 RAG 模式：只基于文本证据调用 DeepSeek，不使用图谱路径。"""
    prompt = f"""用户问题：
{question}

文本证据：
{_format_text_evidence(text_evidence)}

请只基于文本证据生成答案。"""
    return _call_deepseek(settings, SYSTEM_PROMPT, prompt)
