from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

from common import mock_embedding, read_sample_json
from app.core.config import get_settings


COLLECTION_NAME = "cyber_doc_chunks"
VECTOR_DIM = 64


def create_collection() -> Collection:
    if utility.has_collection(COLLECTION_NAME):
        return Collection(COLLECTION_NAME)

    fields = [
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=128, is_primary=True),
        FieldSchema(name="entity_id", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="entity_type", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
    ]
    schema = CollectionSchema(fields=fields, description="Cyber security document chunks")
    collection = Collection(COLLECTION_NAME, schema=schema)
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
    collection = create_collection()

    # 为了保持脚本幂等，样例集合每次先清空再写入；真实数据导入时再改为增量 upsert。
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
            [mock_embedding(item["text"], VECTOR_DIM) for item in doc_chunks],
        ]
    )
    collection.flush()
    collection.load()

    print(f"Milvus import done: {collection.num_entities} doc chunks in {COLLECTION_NAME}")
    connections.disconnect("default")


if __name__ == "__main__":
    main()
