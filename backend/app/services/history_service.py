from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    JSON,
    MetaData,
    String,
    Table,
    Text,
    delete,
    func,
    select,
    text,
)

from app.core.config import Settings
from app.db.postgres import create_postgres_engine
from app.schemas.history import HistoryItem, HistoryListResponse, HistoryStats
from app.schemas.qa import QaResponse


metadata = MetaData()

qa_history_table = Table(
    "qa_history",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("question", Text, nullable=False),
    Column("answer", Text, nullable=False),
    Column("mode", String(32), nullable=False, default="KG-RAG"),
    Column("confidence", Float, nullable=False),
    Column("elapsed_ms", Integer, nullable=False),
    Column("graph_path_count", Integer, nullable=False),
    Column("text_evidence_count", Integer, nullable=False),
    Column("graph_paths", JSON, nullable=False, default=list),
    Column("text_evidence", JSON, nullable=False, default=list),
    Column("created_at", DateTime(timezone=True), nullable=False),
)


def ensure_history_table(settings: Settings) -> None:
    """确保问答历史表存在，避免当前阶段额外引入迁移工具。"""
    engine = create_postgres_engine(settings)
    try:
        with engine.begin() as connection:
            metadata.create_all(connection)
            # 兼容旧版本已创建的 qa_history 表，补齐完整证据落库字段。
            connection.execute(
                text("ALTER TABLE qa_history ADD COLUMN IF NOT EXISTS graph_paths JSONB NOT NULL DEFAULT '[]'::jsonb")
            )
            connection.execute(
                text("ALTER TABLE qa_history ADD COLUMN IF NOT EXISTS text_evidence JSONB NOT NULL DEFAULT '[]'::jsonb")
            )
    finally:
        engine.dispose()


def save_qa_history(settings: Settings, response: QaResponse, elapsed_ms: int, mode: str = "KG-RAG") -> int:
    """保存一次问答结果，供历史页和统计页复用。"""
    ensure_history_table(settings)
    engine = create_postgres_engine(settings)
    try:
        with engine.begin() as connection:
            result = connection.execute(
                qa_history_table.insert()
                .values(
                    question=response.question,
                    answer=response.answer,
                    mode=mode,
                    confidence=response.confidence,
                    elapsed_ms=elapsed_ms,
                    graph_path_count=len(response.graph_paths),
                    text_evidence_count=len(response.text_evidence),
                    graph_paths=response.graph_paths,
                    text_evidence=[evidence.model_dump() for evidence in response.text_evidence],
                    created_at=datetime.now(UTC),
                )
                .returning(qa_history_table.c.id)
            )
            return int(result.scalar_one())
    finally:
        engine.dispose()


def list_qa_history(settings: Settings, page: int = 1, page_size: int = 10, keyword: str = "") -> HistoryListResponse:
    """分页查询问答历史，keyword 同时匹配问题和答案。"""
    ensure_history_table(settings)
    offset = (page - 1) * page_size
    engine = create_postgres_engine(settings)
    try:
        with engine.connect() as connection:
            condition = None
            if keyword:
                pattern = f"%{keyword}%"
                condition = qa_history_table.c.question.ilike(pattern) | qa_history_table.c.answer.ilike(pattern)

            count_statement = select(func.count()).select_from(qa_history_table)
            data_statement = select(qa_history_table).order_by(qa_history_table.c.created_at.desc()).offset(offset).limit(page_size)
            if condition is not None:
                count_statement = count_statement.where(condition)
                data_statement = data_statement.where(condition)

            total = int(connection.execute(count_statement).scalar_one())
            rows = connection.execute(data_statement).mappings().all()
            items = [HistoryItem(**dict(row)) for row in rows]
            return HistoryListResponse(items=items, total=total, page=page, page_size=page_size)
    finally:
        engine.dispose()


def get_history_stats(settings: Settings) -> HistoryStats:
    """统计问答次数、平均置信度和平均耗时。"""
    ensure_history_table(settings)
    engine = create_postgres_engine(settings)
    try:
        with engine.connect() as connection:
            row = connection.execute(
                select(
                    func.count().label("total"),
                    func.avg(qa_history_table.c.confidence).label("avg_confidence"),
                    func.avg(qa_history_table.c.elapsed_ms).label("avg_elapsed_ms"),
                )
            ).one()
            kg_rag_count = int(
                connection.execute(
                    select(func.count()).where(qa_history_table.c.mode == "KG-RAG")
                ).scalar_one()
            )
            return HistoryStats(
                total=int(row.total),
                avg_confidence=float(row.avg_confidence) if row.avg_confidence is not None else None,
                avg_elapsed_ms=float(row.avg_elapsed_ms) if row.avg_elapsed_ms is not None else None,
                kg_rag_count=kg_rag_count,
            )
    finally:
        engine.dispose()


def delete_history_item(settings: Settings, history_id: int) -> bool:
    """删除单条问答历史。"""
    ensure_history_table(settings)
    engine = create_postgres_engine(settings)
    try:
        with engine.begin() as connection:
            result = connection.execute(delete(qa_history_table).where(qa_history_table.c.id == history_id))
            return result.rowcount > 0
    finally:
        engine.dispose()
