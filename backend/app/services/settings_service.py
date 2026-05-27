from app.core.config import Settings
from app.db.milvus import check_milvus
from app.db.neo4j import check_neo4j
from app.db.postgres import check_postgres
from app.schemas.settings import BasicSetting, ConnectionSetting, ModelSetting, SettingsResponse


def _check_status(settings: Settings, checker) -> tuple[str, str]:
    try:
        checker(settings)
        return "ok", "连接正常"
    except Exception as exc:  # noqa: BLE001 - 设置页要展示各依赖的独立错误
        return "error", str(exc)


def build_public_settings(settings: Settings) -> SettingsResponse:
    """构建系统设置页公开配置，明确不返回任何 API Key 或密码。"""
    postgres_status, postgres_message = _check_status(settings, check_postgres)
    neo4j_status, neo4j_message = _check_status(settings, check_neo4j)
    milvus_status, milvus_message = _check_status(settings, check_milvus)

    return SettingsResponse(
        basic=BasicSetting(
            system_name="CyberKG-RAG 网络安全智能问答平台",
            description="面向网络安全场景的知识图谱驱动问答系统",
            default_qa_mode="KG-RAG",
            language="简体中文",
            timezone="Asia/Shanghai",
        ),
        model=ModelSetting(
            embedding_provider=settings.embedding_provider,
            embedding_model=settings.embedding_model,
            embedding_dim=settings.embedding_dim,
            milvus_collection=settings.milvus_collection,
            dashscope_configured=bool(settings.dashscope_api_key.strip()),
            deepseek_configured=bool(settings.deepseek_api_key.strip()),
        ),
        connections=[
            ConnectionSetting(
                name="PostgreSQL",
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
                status=postgres_status,
                message=postgres_message,
            ),
            ConnectionSetting(
                name="Neo4j",
                host=settings.neo4j_uri,
                port="7687",
                database="neo4j",
                status=neo4j_status,
                message=neo4j_message,
            ),
            ConnectionSetting(
                name="Milvus",
                host=settings.milvus_host,
                port=settings.milvus_port,
                database=settings.milvus_collection,
                status=milvus_status,
                message=milvus_message,
            ),
        ],
        reserved_sections=["提示词模板", "日志管理", "权限控制"],
    )
