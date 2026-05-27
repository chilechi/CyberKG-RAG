from fastapi import APIRouter

from app.schemas.common import ApiResponse
from app.schemas.overview import ReservedApiResponse


router = APIRouter()


@router.get("/experiments/qa-comparison", response_model=ApiResponse[ReservedApiResponse])
def get_qa_comparison() -> ApiResponse[ReservedApiResponse]:
    """问答对比实验后续接入评测任务与指标表。"""
    return ApiResponse(data=ReservedApiResponse(message="问答对比实验接口预留，尚未接入评测数据"))


@router.get("/experiments/kg-completion", response_model=ApiResponse[ReservedApiResponse])
def get_kg_completion() -> ApiResponse[ReservedApiResponse]:
    """知识补全实验后续接入 PyKEEN 训练结果。"""
    return ApiResponse(data=ReservedApiResponse(message="知识补全实验接口预留，尚未接入训练结果"))
