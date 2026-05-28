from pydantic import BaseModel, Field


class KgCompletionModelMetric(BaseModel):
    """知识补全模型评估指标。"""

    model: str
    mrr: float = Field(..., ge=0.0, le=1.0)
    hits_at_1: float = Field(..., ge=0.0, le=1.0)
    hits_at_3: float = Field(..., ge=0.0, le=1.0)
    hits_at_10: float = Field(..., ge=0.0, le=1.0)
    train_seconds: int


class KgCompletionCurvePoint(BaseModel):
    """训练曲线中的单个轮次指标点。"""

    epoch: int
    transe: float
    complex: float
    rotate: float


class KgCompletionDataset(BaseModel):
    """知识补全实验使用的数据集统计。"""

    entity_count: int
    relation_count: int
    triple_count: int
    train_count: int
    valid_count: int
    test_count: int
    entity_types: dict[str, int]
    relation_types: dict[str, int]


class KgCompletionResponse(BaseModel):
    """知识补全实验总览响应。"""

    dataset: KgCompletionDataset
    model_metrics: list[KgCompletionModelMetric]
    mrr_curve: list[KgCompletionCurvePoint]
    hits_at_10_curve: list[KgCompletionCurvePoint]
    loss_curve: list[KgCompletionCurvePoint]
    conclusion: str


class KgCompletionPredictRequest(BaseModel):
    """Top-K 尾实体预测请求。"""

    head: str = Field(..., min_length=1)
    relation: str = Field(..., min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)


class KgCompletionPrediction(BaseModel):
    """Top-K 补全候选结果。"""

    rank: int
    tail: str
    tail_name: str
    tail_type: str
    score: float = Field(..., ge=0.0, le=1.0)
    reason: str


class KgCompletionPredictResponse(BaseModel):
    """Top-K 尾实体预测响应。"""

    head: str
    relation: str
    predictions: list[KgCompletionPrediction]
