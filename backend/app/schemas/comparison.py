from pydantic import BaseModel, Field

from app.schemas.qa import QaEvidence


class QaComparisonRequest(BaseModel):
    """问答对比实验请求。"""

    question: str = Field(..., min_length=1, description="用于对比三种问答模式的问题")


class QaComparisonResult(BaseModel):
    """单个问答模式的实验结果。"""

    mode: str
    answer: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    elapsed_ms: int
    graph_path_count: int
    text_evidence_count: int
    graph_paths: list[list[str]]
    text_evidence: list[QaEvidence]


class QaComparisonMetric(BaseModel):
    """对比实验的聚合指标。"""

    best_mode: str
    fastest_mode: str
    max_confidence: float
    total_elapsed_ms: int


class QaComparisonResponse(BaseModel):
    """问答对比实验响应。"""

    question: str
    results: list[QaComparisonResult]
    metrics: QaComparisonMetric
