from fastapi import APIRouter

from app.schemas.common import ApiResponse
from app.schemas.graph import GraphData, GraphEdge, GraphNode
from app.schemas.qa import QaEvidence, QaRequest, QaResponse
from app.services.sample_data import load_doc_chunks, load_entities, load_relations


router = APIRouter()


@router.get("/graph", response_model=ApiResponse[GraphData])
def get_mock_graph() -> ApiResponse[GraphData]:
    """返回固定样例图谱，先服务前端 ECharts 联调。"""
    graph = GraphData(
        nodes=[GraphNode(**entity) for entity in load_entities()],
        edges=[GraphEdge(**relation) for relation in load_relations()],
    )
    return ApiResponse(data=graph, message="mock graph loaded")


@router.post("/qa", response_model=ApiResponse[QaResponse])
def ask_mock_question(request: QaRequest) -> ApiResponse[QaResponse]:
    """返回固定问答结果，用于先约定前端展示字段。"""
    # 这里先不接 DeepSeek，也不查库；目标是提前稳定问答接口形状。
    chunks = load_doc_chunks()
    response = QaResponse(
        question=request.question,
        answer=(
            "Log4Shell 可被理解为一个与不可信数据反序列化相关的远程代码执行漏洞。"
            "在样例图谱中，它通过 CWE-502 关联到 CAPEC-586，并进一步关联到 "
            "MITRE ATT&CK 技术 T1190，属于 Initial Access 战术。"
        ),
        graph_paths=[
            [
                "CVE-2021-44228",
                "CWE-502",
                "CAPEC-586",
                "T1190",
                "TA0001",
            ]
        ],
        text_evidence=[QaEvidence(**chunk) for chunk in chunks],
        confidence=0.88,
    )
    return ApiResponse(data=response, message="mock answer generated")
