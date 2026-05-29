from time import perf_counter

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.common import ApiResponse
from app.schemas.qa import QaRequest, QaResponse
from app.services.confidence_service import calculate_llm_confidence, calculate_rag_confidence
from app.services.history_service import save_qa_history
from app.services.llm_service import generate_free_answer, generate_rag_answer
from app.services.rag_service import answer_with_kg_rag
from app.services.vector_service import search_doc_chunks


router = APIRouter()


def _fallback_llm_answer(question: str) -> str:
    return (
        f"针对问题“{question}”，普通 LLM 模式需要 DeepSeek API Key 才能生成无检索增强答案。"
        "当前未获得可用模型回复，因此无法给出可靠结论。"
    )


def _fallback_rag_answer(question: str, evidence_count: int) -> str:
    if evidence_count == 0:
        return (
            f"针对问题“{question}”，普通 RAG 模式没有召回到文本证据。"
            "为了避免无依据生成，当前不输出结论。"
        )
    return (
        f"针对问题“{question}”，普通 RAG 模式召回了 {evidence_count} 条文本证据，"
        "但 DeepSeek 当前未配置或调用失败，因此只返回检索结果，不生成扩展答案。"
    )


def _answer_with_llm(settings: Settings, question: str) -> QaResponse:
    model_answer = generate_free_answer(settings, question)
    answer = model_answer or _fallback_llm_answer(question)
    return QaResponse(
        question=question,
        mode="普通 LLM",
        answer=answer,
        graph_paths=[],
        text_evidence=[],
        confidence=calculate_llm_confidence(model_answer is not None),
    )


def _answer_with_rag(settings: Settings, question: str) -> QaResponse:
    try:
        text_evidence = search_doc_chunks(settings, query=question, top_k=5)
    except Exception:  # noqa: BLE001 - Milvus 异常时仍返回可解释的降级结果
        text_evidence = []
    model_answer = generate_rag_answer(settings, question, text_evidence)
    answer = model_answer or _fallback_rag_answer(question, len(text_evidence))
    return QaResponse(
        question=question,
        mode="普通 RAG",
        answer=answer,
        graph_paths=[],
        text_evidence=text_evidence,
        confidence=calculate_rag_confidence(text_evidence, model_answer is not None),
    )


def _answer_by_mode(settings: Settings, question: str, mode: str) -> QaResponse:
    normalized_mode = mode.strip().lower()
    if normalized_mode == "llm":
        return _answer_with_llm(settings, question)
    if normalized_mode == "rag":
        return _answer_with_rag(settings, question)
    return answer_with_kg_rag(settings, question)


@router.post("/ask", response_model=ApiResponse[QaResponse])
def ask_question(request: QaRequest, settings: Settings = Depends(get_settings)) -> ApiResponse[QaResponse]:
    """按用户选择的模式执行问答，并把结果写入问答历史。"""
    started_at = perf_counter()
    response = _answer_by_mode(settings, request.question, request.mode)
    elapsed_ms = int((perf_counter() - started_at) * 1000)
    save_qa_history(settings, response=response, elapsed_ms=elapsed_ms, mode=response.mode)
    return ApiResponse(data=response, message="answer generated")
