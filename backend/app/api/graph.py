from typing import Annotated

from fastapi import APIRouter, Query

from app.core.config import get_settings
from app.schemas.common import ApiResponse
from app.schemas.graph import GraphData
from app.services.graph_service import get_neighbor_graph


router = APIRouter()


@router.get("/neighbors", response_model=ApiResponse[GraphData])
def get_graph_neighbors(
    entity_id: Annotated[str, Query(min_length=1, description="起始实体 ID")],
    depth: Annotated[int, Query(ge=1, le=4, description="查询跳数，限制 1-4 跳")] = 2,
) -> ApiResponse[GraphData]:
    """从 Neo4j 查询实体邻居子图。"""
    graph = get_neighbor_graph(get_settings(), entity_id=entity_id, depth=depth)
    message = "graph loaded" if graph.nodes else "entity not found or no neighbors"
    return ApiResponse(data=graph, message=message)
