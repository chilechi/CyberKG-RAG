from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

from common import read_sample_json
from app.core.config import get_settings
from app.services.embedding_service import embed_text


def create_collection(collection_name: str, vector_dim: int) -> Collection:
    """样例数据导入每次重建 collection，保证统计值和样例文件完全一致。"""
    if utility.has_collection(collection_name):
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
