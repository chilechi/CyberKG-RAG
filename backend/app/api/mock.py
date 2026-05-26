from fastapi import APIRouter

from app.schemas.common import ApiResponse
from app.schemas.graph import GraphData, GraphEdge, GraphNode
from app.schemas.qa import QaEvidence, QaRequest, QaResponse


router = APIRouter()


@router.get("/graph", response_model=ApiResponse[GraphData])
def get_mock_graph() -> ApiResponse[GraphData]:
    """返回固定样例图谱，先服务前端 ECharts 联调。"""
    graph = GraphData(
        nodes=[
            GraphNode(
                id="CVE-2021-44228",
                name="Log4Shell",
                type="Vulnerability",
                description="Apache Log4j2 远程代码执行漏洞。",
            ),
            GraphNode(
                id="CWE-502",
                name="Deserialization of Untrusted Data",
                type="Weakness",
                description="不可信数据反序列化弱点。",
            ),
            GraphNode(
                id="CAPEC-586",
                name="Object Injection",
                type="AttackPattern",
                description="对象注入攻击模式。",
            ),
            GraphNode(
                id="T1190",
                name="Exploit Public-Facing Application",
                type="Technique",
                description="利用公网暴露应用的 ATT&CK 技术。",
            ),
            GraphNode(
                id="TA0001",
                name="Initial Access",
                type="Tactic",
                description="初始访问战术。",
            ),
        ],
        edges=[
            GraphEdge(
                source="CVE-2021-44228",
                target="CWE-502",
                relation="HAS_WEAKNESS",
            ),
            GraphEdge(
                source="CWE-502",
                target="CAPEC-586",
                relation="RELATED_TO_CAPEC",
            ),
            GraphEdge(
                source="CAPEC-586",
                target="T1190",
                relation="USES_TECHNIQUE",
            ),
            GraphEdge(
                source="T1190",
                target="TA0001",
                relation="BELONGS_TO_TACTIC",
            ),
        ],
    )
    return ApiResponse(data=graph, message="mock graph loaded")


@router.post("/qa", response_model=ApiResponse[QaResponse])
def ask_mock_question(request: QaRequest) -> ApiResponse[QaResponse]:
    """返回固定问答结果，用于先约定前端展示字段。"""
    # 这里先不接 DeepSeek，也不查库；目标是提前稳定问答接口形状。
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
        text_evidence=[
            QaEvidence(
                source="NVD",
                entity_id="CVE-2021-44228",
                text="Apache Log4j2 远程代码执行漏洞样例描述。",
                score=0.92,
            ),
            QaEvidence(
                source="MITRE ATT&CK",
                entity_id="T1190",
                text="T1190 表示利用公网暴露应用以获得初始访问。",
                score=0.86,
            ),
        ],
        confidence=0.88,
    )
    return ApiResponse(data=response, message="mock answer generated")
