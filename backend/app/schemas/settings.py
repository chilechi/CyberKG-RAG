from pydantic import BaseModel


class ConnectionSetting(BaseModel):
    """数据库连接公开信息和探活状态。"""

    name: str
    host: str
    port: int | str
    database: str = ""
    status: str
    message: str = ""


class ModelSetting(BaseModel):
    """模型和向量化配置，敏感 key 不返回。"""

    embedding_provider: str
    embedding_model: str
    embedding_dim: int
    milvus_collection: str
    dashscope_configured: bool
    deepseek_configured: bool


class BasicSetting(BaseModel):
    """系统基础配置。"""

    system_name: str
    description: str
    default_qa_mode: str
    language: str
    timezone: str


class SettingsResponse(BaseModel):
    """系统设置页响应。"""

    basic: BasicSetting
    model: ModelSetting
    connections: list[ConnectionSetting]
