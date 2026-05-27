from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.common import ApiResponse
from app.schemas.overview import ReservedApiResponse


router = APIRouter()


@router.get("/history", response_model=ApiResponse[ReservedApiResponse])
def get_question_history() -> ApiResponse[ReservedApiResponse]:
    """问答历史后续接入持久化日志表，目前只返回预留接口。"""
    return ApiResponse(data=ReservedApiResponse(message="问答历史模块预留，尚未接入日志表"))


@router.get("/experiments/qa-comparison", response_model=ApiResponse[ReservedApiResponse])
def get_qa_comparison() -> ApiResponse[ReservedApiResponse]:
    """问答对比实验后续接入评测任务与指标表。"""
    return ApiResponse(data=ReservedApiResponse(message="问答对比实验接口预留，尚未接入评测数据"))


@router.get("/experiments/kg-completion", response_model=ApiResponse[ReservedApiResponse])
def get_kg_completion() -> ApiResponse[ReservedApiResponse]:
    """知识补全实验后续接入 PyKEEN 训练结果。"""
    return ApiResponse(data=ReservedApiResponse(message="知识补全实验接口预留，尚未接入训练结果"))


@router.get("/settings", response_model=ApiResponse[dict])
def get_public_settings(settings: Settings = Depends(get_settings)) -> ApiResponse[dict]:
    """只返回可公开展示的配置，避免泄露 API Key。"""
    return ApiResponse(
        data={
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
            "embedding_dim": settings.embedding_dim,
            "milvus_collection": settings.milvus_collection,
        },
        message="public settings loaded",
    )
