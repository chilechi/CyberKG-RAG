from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.common import ApiResponse
from app.schemas.overview import OverviewSummary
from app.services.overview_service import build_overview_summary


router = APIRouter()


@router.get("/summary", response_model=ApiResponse[OverviewSummary])
def get_overview_summary(settings: Settings = Depends(get_settings)) -> ApiResponse[OverviewSummary]:
    """返回系统总览页需要的真实聚合指标。"""
    return ApiResponse(data=build_overview_summary(settings), message="overview summary loaded")
