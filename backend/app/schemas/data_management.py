from pydantic import BaseModel


class DataMetric(BaseModel):
    """数据管理页顶部指标。"""

    key: str
    label: str
    value: int | None
    description: str = ""
    status: str = "ready"


class DataSourceItem(BaseModel):
    """数据源概况，统计值来自 PostgreSQL 文档片段表。"""

    name: str
    source_type: str
    storage_targets: list[str]
    document_count: int
    status: str = "ready"


class DataImportStep(BaseModel):
    """数据导入流程步骤。"""

    key: str
    label: str
    description: str
    count: int | None = None
    status: str = "ready"


class DataManagementSummary(BaseModel):
    """数据管理页聚合响应。"""

    metrics: list[DataMetric]
    sources: list[DataSourceItem]
    import_steps: list[DataImportStep]
