from pymilvus import Collection, connections

from common import BACKEND_DIR  # noqa: F401 - 导入 common 会把 backend 加入 sys.path
from app.core.config import get_settings


DATA_TYPE_NAMES = {
    1: "BOOL",
    2: "INT8",
    3: "INT16",
    4: "INT32",
    5: "INT64",
    10: "FLOAT",
    11: "DOUBLE",
    20: "STRING",
    21: "VARCHAR",
    100: "BINARY_VECTOR",
    101: "FLOAT_VECTOR",
    102: "FLOAT16_VECTOR",
    103: "BFLOAT16_VECTOR",
}


def data_type_name(dtype) -> str:
    return DATA_TYPE_NAMES.get(int(dtype), str(dtype))


def main() -> None:
    settings = get_settings()
    connections.connect(host=settings.milvus_host, port=str(settings.milvus_port))
    collection = Collection(settings.milvus_collection)
    collection.load()

    print("=" * 80)
    print("Milvus 向量库说明")
    print("=" * 80)
    print("Milvus 保存的是 doc_chunks.text 转出来的 embedding 向量，用于语义相似度检索。")
    print("它不保存图谱边，图谱边在 PostgreSQL relations 和 Neo4j 中。")
    print("核心关联字段是 entity_id，对应 PostgreSQL entities.id 和 Neo4j 节点 id。")

    print("\nCollection：", settings.milvus_collection)
    print("向量数量：", collection.num_entities)

    print("\n字段含义：")
    field_meanings = {
        "chunk_id": "文档片段唯一 ID，对应 PostgreSQL doc_chunks.chunk_id。",
        "entity_id": "片段关联实体 ID，对应 PostgreSQL entities.id 和 Neo4j 节点 id。",
        "entity_type": "实体类型，例如 Vulnerability、Weakness、Technique。",
        "source": "文本来源，例如 NVD、MITRE CWE、Security Advisory。",
        "text": "原始文本片段，用于作为 RAG 文本证据返回。",
        "embedding": "文本向量，由阿里 text-embedding-v4 或 mock embedding 生成。",
    }
    for field in collection.schema.fields:
        print(f"- {field.name}: {data_type_name(field.dtype)}；{field_meanings.get(field.name, '')}")

    print("\n样例数据：")
    rows = collection.query(
        expr='chunk_id != ""',
        output_fields=["chunk_id", "entity_id", "entity_type", "source", "text"],
        limit=5,
    )
    for row in rows:
        text_preview = str(row.get("text", ""))[:120]
        print(
            f"- {row.get('chunk_id')} / {row.get('entity_id')} / "
            f"{row.get('entity_type')} / {row.get('source')}: {text_preview}..."
        )

    connections.disconnect("default")


if __name__ == "__main__":
    main()
