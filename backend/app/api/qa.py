from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import ApiResponse
from app.schemas.qa import QaRequest, QaResponse
from app.services.rag_service import answer_with_kg_rag


router = APIRouter()


@router.post("/ask", response_model=ApiResponse[QaResponse])
def ask_question(request: QaRequest) -> ApiResponse[QaResponse]:
    """KG-RAG 问答接口：融合 Neo4j 图谱证据和 Milvus 文本证据。"""
    response = answer_with_kg_rag(get_settings(), request.question)
    return ApiResponse(data=response, message="kg-rag answer generated")
