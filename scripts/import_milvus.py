from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

from common import read_sample_json
from app.core.config import get_settings
from app.services.embedding_service import embed_text


def create_collection(collection_name: str, vector_dim: int) -> Collection:
    if utility.has_collection(collection_name):
        collection = Collection(collection_name)
        existing_dim = next(
            field.params.get("dim")
            for field in collection.schema.fields
            if field.name == "embedding"
        )
        if int(existing_dim) == vector_dim:
            return collection
        # embedding 维度变化时必须重建 collection，否则 Milvus 会拒绝写入。
        utility.drop_collection(collection_name)

    fields = [
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=128, is_primary=True),
        FieldSchema(name="entity_id", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="entity_type", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=vector_dim),
    ]
    schema = CollectionSchema(fields=fields, description="Cyber security document chunks")
    collection = Collection(collection_name, schema=schema)
    collection.create_index(
        field_name="embedding",
        index_params={
            "metric_type": "COSINE",
            "index_type": "AUTOINDEX",
            "params": {},
        },
    )
    return collection


def main() -> None:
    settings = get_settings()
    connections.connect(host=settings.milvus_host, port=str(settings.milvus_port))
    doc_chunks = read_sample_json("doc_chunks.json")
    collection = create_collection(settings.milvus_collection, settings.embedding_dim)

    # 样例导入脚本保持幂等：每次先清空再写入；真实数据导入时再改为增量 upsert。
    if collection.num_entities > 0:
        collection.delete(expr='chunk_id != ""')
        collection.flush()

    collection.insert(
        [
            [item["chunk_id"] for item in doc_chunks],
            [item["entity_id"] for item in doc_chunks],
            [item["entity_type"] for item in doc_chunks],
            [item["source"] for item in doc_chunks],
            [item["text"] for item in doc_chunks],
            [embed_text(settings, item["text"]) for item in doc_chunks],
        ]
    )
    collection.flush()
    collection.load()

    print(
        f"Milvus import done: {collection.num_entities} doc chunks in {settings.milvus_collection} "
        f"with {settings.embedding_provider}/{settings.embedding_model}"
    )
    connections.disconnect("default")


if __name__ == "__main__":
    main()
