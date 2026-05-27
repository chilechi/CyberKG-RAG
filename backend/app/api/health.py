from fastapi import APIRouter

from app.core.config import get_settings
from app.db.milvus import check_milvus
from app.db.neo4j import check_neo4j
from app.db.postgres import check_postgres
from app.schemas.common import ApiResponse


router = APIRouter()


def _run_check(name: str, checker) -> dict[str, str]:
    try:
        checker(get_settings())
        return {"name": name, "status": "ok", "message": ""}
    except Exception as exc:  # noqa: BLE001 - 健康检查需要捕获所有连接异常并返回给前端
        return {"name": name, "status": "error", "message": str(exc)}


@router.get("/dependencies", response_model=ApiResponse[list[dict[str, str]]])
def check_dependencies() -> ApiResponse[list[dict[str, str]]]:
    """检查 PostgreSQL、Neo4j、Milvus 是否都能从后端连通。"""
    results = [
        _run_check("postgres", check_postgres),
        _run_check("neo4j", check_neo4j),
        _run_check("milvus", check_milvus),
    ]
    success = all(item["status"] == "ok" for item in results)
    return ApiResponse(
        success=success,
        data=results,
        message="dependencies checked" if success else "some dependencies failed",
    )
