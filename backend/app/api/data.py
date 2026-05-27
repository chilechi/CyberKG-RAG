from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.common import ApiResponse
from app.schemas.data_management import DataManagementSummary, DataSourceItem
from app.services.data_management_service import build_data_management_summary


router = APIRouter()


@router.get("/summary", response_model=ApiResponse[DataManagementSummary])
def get_data_summary(settings: Settings = Depends(get_settings)) -> ApiResponse[DataManagementSummary]:
    """返回数据管理页需要的真实数据规模、来源和导入流程。"""
    return ApiResponse(data=build_data_management_summary(settings), message="data summary loaded")


@router.get("/sources", response_model=ApiResponse[list[DataSourceItem]])
def get_data_sources(settings: Settings = Depends(get_settings)) -> ApiResponse[list[DataSourceItem]]:
    """保留独立数据源接口，前端表格也可单独复用。"""
    summary = build_data_management_summary(settings)
    return ApiResponse(data=summary.sources, message="data sources loaded")
