from time import perf_counter

from app.core.config import Settings
from app.schemas.comparison import QaComparisonMetric, QaComparisonResponse, QaComparisonResult
from app.services.llm_service import generate_free_answer, generate_rag_answer
from app.services.rag_service import answer_with_kg_rag
from app.services.vector_service import search_doc_chunks


def _elapsed_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)


def _fallback_llm_answer(question: str) -> str:
    return (
        f"针对问题“{question}”，普通 LLM 模式需要 DeepSeek API Key 才能生成无检索增强答案。"
        "当前未获得可用模型回复，因此无法给出可靠结论。"
    )


def _fallback_rag_answer(question: str, evidence_count: int) -> str:
    if evidence_count == 0:
        return (
            f"针对问题“{question}”，普通 RAG 模式没有召回到文本证据。"
            "为了避免无依据生成，暂不输出结论。"
        )
    return (
        f"针对问题“{question}”，普通 RAG 模式召回了 {evidence_count} 条文本证据，"
        "但 DeepSeek 当前未配置或调用失败，因此只返回检索结果，不生成扩展答案。"
    )


def run_qa_comparison(settings: Settings, question: str) -> QaComparisonResponse:
    """依次运行普通 LLM、普通 RAG、KG-RAG，形成可展示的对比结果。"""
    results: list[QaComparisonResult] = []

    started_at = perf_counter()
    llm_answer = generate_free_answer(settings, question) or _fallback_llm_answer(question)
    results.append(
        QaComparisonResult(
            mode="普通 LLM",
            answer=llm_answer,
            confidence=0.45 if settings.deepseek_api_key.strip() else 0.15,
            elapsed_ms=_elapsed_ms(started_at),
            graph_path_count=0,
            text_evidence_count=0,
            graph_paths=[],
            text_evidence=[],
        )
    )

    started_at = perf_counter()
    try:
        text_evidence = search_doc_chunks(settings, query=question, top_k=5)
    except Exception:  # noqa: BLE001 - 对比实验允许 Milvus 失败后继续展示其它模式
        text_evidence = []
    rag_answer = generate_rag_answer(settings, question, text_evidence) or _fallback_rag_answer(question, len(text_evidence))
    results.append(
        QaComparisonResult(
            mode="普通 RAG",
            answer=rag_answer,
            confidence=min(0.75, 0.25 + len(text_evidence) * 0.08),
            elapsed_ms=_elapsed_ms(started_at),
            graph_path_count=0,
            text_evidence_count=len(text_evidence),
            graph_paths=[],
            text_evidence=text_evidence,
        )
    )

    started_at = perf_counter()
    kg_rag_answer = answer_with_kg_rag(settings, question)
    results.append(
        QaComparisonResult(
            mode="KG-RAG",
            answer=kg_rag_answer.answer,
            confidence=kg_rag_answer.confidence,
            elapsed_ms=_elapsed_ms(started_at),
            graph_path_count=len(kg_rag_answer.graph_paths),
            text_evidence_count=len(kg_rag_answer.text_evidence),
            graph_paths=kg_rag_answer.graph_paths,
            text_evidence=kg_rag_answer.text_evidence,
        )
    )

    best_result = max(results, key=lambda item: item.confidence)
    fastest_result = min(results, key=lambda item: item.elapsed_ms)
    return QaComparisonResponse(
        question=question,
        results=results,
        metrics=QaComparisonMetric(
            best_mode=best_result.mode,
            fastest_mode=fastest_result.mode,
            max_confidence=best_result.confidence,
            total_elapsed_ms=sum(item.elapsed_ms for item in results),
        ),
    )
