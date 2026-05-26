from typing import Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一接口响应结构，便于前端稳定处理 success/data/message。"""

    success: bool = True
    data: T | None = None
    message: str = ""
