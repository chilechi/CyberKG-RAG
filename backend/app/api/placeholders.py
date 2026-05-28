from fastapi import APIRouter
from fastapi import Depends

from app.core.config import Settings, get_settings
from app.schemas.comparison import QaComparisonRequest, QaComparisonResponse
from app.schemas.common import ApiResponse
from app.schemas.overview import ReservedApiResponse
from app.services.comparison_service import run_qa_comparison


router = APIRouter()


@router.get("/experiments/qa-comparison", response_model=ApiResponse[ReservedApiResponse])
def get_qa_comparison() -> ApiResponse[ReservedApiResponse]:
    """问答对比实验后续接入评测任务与指标表。"""
    return ApiResponse(data=ReservedApiResponse(message="问答对比实验接口预留，尚未接入评测数据"))


@router.post("/experiments/qa-comparison", response_model=ApiResponse[QaComparisonResponse])
def run_qa_comparison_experiment(
    request: QaComparisonRequest,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[QaComparisonResponse]:
    """运行普通 LLM、普通 RAG、KG-RAG 三种问答模式的实时对比实验。"""
    return ApiResponse(data=run_qa_comparison(settings, request.question), message="qa comparison finished")


@router.get("/experiments/kg-completion", response_model=ApiResponse[ReservedApiResponse])
def get_kg_completion() -> ApiResponse[ReservedApiResponse]:
    """知识补全实验后续接入 PyKEEN 训练结果。"""
    return ApiResponse(data=ReservedApiResponse(message="知识补全实验接口预留，尚未接入训练结果"))
