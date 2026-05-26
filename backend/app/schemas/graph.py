from pydantic import BaseModel


class GraphNode(BaseModel):
    """图谱节点：前端 ECharts 使用 id/name/type 做渲染和分类。"""

    id: str
    name: str
    type: str
    description: str = ""


class GraphEdge(BaseModel):
    """图谱边：source/target 对应节点 id，relation 对应关系类型。"""

    source: str
    target: str
    relation: str


class GraphData(BaseModel):
    """图谱接口返回数据。"""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
