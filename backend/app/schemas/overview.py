from pydantic import BaseModel


class MetricCard(BaseModel):
    """系统总览中的指标卡片，value 为 None 时前端展示为预留状态。"""

    key: str
    label: str
    value: int | float | None
    unit: str = ""
    status: str = "ready"
    description: str = ""


class DependencyStatus(BaseModel):
    """后端依赖服务状态。"""

    name: str
    status: str
    message: str = ""


class DistributionItem(BaseModel):
    """由数据库聚合出的分布项，用于图例、概况和数据源统计。"""

    key: str
    label: str
    count: int


class FlowStep(BaseModel):
    """系统流程步骤，count 来自真实数据或依赖状态。"""

    key: str
    label: str
    description: str
    count: int | None = None
    status: str = "ready"


class OverviewSummary(BaseModel):
    """系统总览页聚合数据。"""

    metrics: list[MetricCard]
    dependencies: list[DependencyStatus]
    entity_types: list[DistributionItem]
    relation_types: list[DistributionItem]
    document_sources: list[DistributionItem]
    flow_steps: list[FlowStep]


class ReservedApiResponse(BaseModel):
    """未完成模块的统一预留响应，避免前端写死演示数据。"""

    implemented: bool = False
    message: str
    items: list[dict] = []
