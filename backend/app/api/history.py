from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import Settings, get_settings
from app.schemas.common import ApiResponse
from app.schemas.history import HistoryListResponse, HistoryStats
from app.services.history_service import delete_history_item, get_history_stats, list_qa_history


router = APIRouter()


@router.get("", response_model=ApiResponse[HistoryListResponse])
def get_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    keyword: str = "",
    settings: Settings = Depends(get_settings),
) -> ApiResponse[HistoryListResponse]:
    """分页查询问答历史。"""
    return ApiResponse(data=list_qa_history(settings, page=page, page_size=page_size, keyword=keyword), message="history loaded")


@router.get("/stats", response_model=ApiResponse[HistoryStats])
def get_stats(settings: Settings = Depends(get_settings)) -> ApiResponse[HistoryStats]:
    """查询问答历史统计。"""
    return ApiResponse(data=get_history_stats(settings), message="history stats loaded")


@router.delete("/{history_id}", response_model=ApiResponse[dict])
def delete_history(history_id: int, settings: Settings = Depends(get_settings)) -> ApiResponse[dict]:
    """删除单条问答历史。"""
    deleted = delete_history_item(settings, history_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="history item not found")
    return ApiResponse(data={"id": history_id}, message="history deleted")
