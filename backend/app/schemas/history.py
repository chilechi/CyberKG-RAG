from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.qa import QaEvidence


class HistoryItem(BaseModel):
    """问答历史记录。"""

    id: int
    question: str
    answer: str
    mode: str
    confidence: float
    elapsed_ms: int
    graph_path_count: int
    text_evidence_count: int
    graph_paths: list[list[str]] = Field(default_factory=list)
    text_evidence: list[QaEvidence] = Field(default_factory=list)
    created_at: datetime


class HistoryListResponse(BaseModel):
    """问答历史分页响应。"""

    items: list[HistoryItem]
    total: int
    page: int
    page_size: int


class HistoryStats(BaseModel):
    """问答历史统计。"""

    total: int
    avg_confidence: float | None = None
    avg_elapsed_ms: float | None = None
    kg_rag_count: int = 0


class HistoryQuery(BaseModel):
    """历史查询参数约束。"""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    keyword: str = ""
