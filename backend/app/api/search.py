from typing import Annotated

from fastapi import APIRouter, Query

from app.core.config import get_settings
from app.schemas.common import ApiResponse
from app.schemas.qa import QaEvidence
from app.services.vector_service import search_doc_chunks


router = APIRouter()


@router.get("/docs", response_model=ApiResponse[list[QaEvidence]])
def search_docs(
    query: Annotated[str, Query(min_length=1, description="检索问题或关键词")],
    top_k: Annotated[int, Query(ge=1, le=10, description="返回条数")] = 3,
) -> ApiResponse[list[QaEvidence]]:
    """从 Milvus 检索文本证据片段。"""
    evidence = search_doc_chunks(get_settings(), query=query, top_k=top_k)
    return ApiResponse(data=evidence, message="documents retrieved")
