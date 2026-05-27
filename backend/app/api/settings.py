from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.common import ApiResponse
from app.schemas.settings import SettingsResponse
from app.services.settings_service import build_public_settings


router = APIRouter()


@router.get("", response_model=ApiResponse[SettingsResponse])
def get_settings_page(settings: Settings = Depends(get_settings)) -> ApiResponse[SettingsResponse]:
    """返回系统设置页公开配置和连接状态，不暴露任何密钥。"""
    return ApiResponse(data=build_public_settings(settings), message="settings loaded")
