from pydantic import BaseModel, Field


class QaRequest(BaseModel):
    """问答请求。"""

    question: str = Field(..., min_length=1, description="用户输入的安全问题")


class QaEvidence(BaseModel):
    """文本证据片段，后续由 Milvus 召回结果填充。"""

    source: str
    entity_id: str
    text: str
    score: float = Field(..., ge=0.0, le=1.0)


class QaResponse(BaseModel):
    """问答响应，提前固定答案、图谱路径、文本证据和置信度字段。"""

    question: str
    answer: str
    graph_paths: list[list[str]]
    text_evidence: list[QaEvidence]
    confidence: float = Field(..., ge=0.0, le=1.0)
