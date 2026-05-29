from sqlalchemy import MetaData, Table, Column, Float, String, Text, create_engine
from sqlalchemy.dialects.postgresql import insert

from common import read_sample_json
from app.core.config import get_settings


metadata = MetaData()

entities_table = Table(
    "entities",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("name", String(256), nullable=False),
    Column("type", String(64), nullable=False),
    Column("description", Text, nullable=False, default=""),
)

relations_table = Table(
    "relations",
    metadata,
    Column("source", String(128), primary_key=True),
    Column("target", String(128), primary_key=True),
    Column("relation", String(128), primary_key=True),
)

doc_chunks_table = Table(
    "doc_chunks",
    metadata,
    Column("chunk_id", String(128), primary_key=True),
    Column("entity_id", String(128), nullable=False),
    Column("entity_type", String(64), nullable=False),
    Column("source", String(128), nullable=False),
    Column("text", Text, nullable=False),
    Column("score", Float, nullable=False, default=0.0),
)


def upsert_rows(connection, table: Table, rows: list[dict]) -> None:
    if not rows:
        return
    statement = insert(table).values(rows)
    update_columns = {
        column.name: statement.excluded[column.name]
        for column in table.columns
        if not column.primary_key
    }
    if not update_columns:
        connection.execute(statement.on_conflict_do_nothing(index_elements=table.primary_key.columns))
        return
    connection.execute(statement.on_conflict_do_update(index_elements=table.primary_key.columns, set_=update_columns))


def delete_missing_rows(connection, table: Table, rows: list[dict], key_columns: list[str]) -> None:
    """以 samples 文件为准清理旧样例数据，避免反复导入后 PostgreSQL 残留过期记录。"""
    if not rows:
        connection.execute(table.delete())
        return
    if len(key_columns) == 1:
        key = key_columns[0]
        values = [row[key] for row in rows]
        connection.execute(table.delete().where(table.c[key].not_in(values)))
        return

    current_keys = {tuple(row[key] for key in key_columns) for row in rows}
    existing_rows = connection.execute(table.select()).mappings().all()
    for existing in existing_rows:
        existing_key = tuple(existing[key] for key in key_columns)
        if existing_key not in current_keys:
            condition = table.c[key_columns[0]] == existing[key_columns[0]]
            for key in key_columns[1:]:
                condition = condition & (table.c[key] == existing[key])
            connection.execute(table.delete().where(condition))


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.postgres_url, pool_pre_ping=True)
    entities = read_sample_json("entities.json")
    relations = read_sample_json("relations.json")
    doc_chunks = read_sample_json("doc_chunks.json")

    # 样例导入脚本要幂等，方便反复执行验证数据库连接和表结构。
    with engine.begin() as connection:
        metadata.create_all(connection)
        delete_missing_rows(connection, entities_table, entities, ["id"])
        delete_missing_rows(connection, relations_table, relations, ["source", "target", "relation"])
        delete_missing_rows(connection, doc_chunks_table, doc_chunks, ["chunk_id"])
        upsert_rows(connection, entities_table, entities)
        upsert_rows(connection, relations_table, relations)
        upsert_rows(connection, doc_chunks_table, doc_chunks)

    print(
        "PostgreSQL import done: "
        f"{len(entities)} entities, {len(relations)} relations, {len(doc_chunks)} doc chunks"
    )


if __name__ == "__main__":
    main()
