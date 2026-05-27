from time import perf_counter

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.common import ApiResponse
from app.schemas.qa import QaRequest, QaResponse
from app.services.history_service import save_qa_history
from app.services.rag_service import answer_with_kg_rag


router = APIRouter()


@router.post("/ask", response_model=ApiResponse[QaResponse])
def ask_question(request: QaRequest, settings: Settings = Depends(get_settings)) -> ApiResponse[QaResponse]:
    """KG-RAG 问答接口：融合 Neo4j 图谱证据和 Milvus 文本证据，并写入问答历史。"""
    started_at = perf_counter()
    response = answer_with_kg_rag(settings, request.question)
    elapsed_ms = int((perf_counter() - started_at) * 1000)
    save_qa_history(settings, response=response, elapsed_ms=elapsed_ms)
    return ApiResponse(data=response, message="kg-rag answer generated")
