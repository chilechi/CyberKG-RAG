from pymilvus import Collection, connections

from app.core.config import Settings
from app.schemas.qa import QaEvidence


COLLECTION_NAME = "cyber_doc_chunks"
VECTOR_DIM = 64


def mock_embedding(text: str, dim: int = VECTOR_DIM) -> list[float]:
    """与导入脚本保持一致的确定性 mock embedding，后续替换为真实 BGE 模型。"""
    import hashlib
    import math

    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < dim:
        for byte in digest:
            values.append((byte / 255.0) * 2.0 - 1.0)
            if len(values) == dim:
                break
        digest = hashlib.sha256(digest).digest()

    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


def search_doc_chunks(settings: Settings, query: str, top_k: int = 3) -> list[QaEvidence]:
    """从 Milvus 检索和问题最相似的文本片段。"""
    connections.connect(host=settings.milvus_host, port=str(settings.milvus_port))
    try:
        collection = Collection(COLLECTION_NAME)
        collection.load()
        results = collection.search(
            data=[mock_embedding(query)],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {}},
            limit=top_k,
            output_fields=["entity_id", "entity_type", "source", "text"],
        )

        evidence: list[QaEvidence] = []
        for hit in results[0]:
            evidence.append(
                QaEvidence(
                    source=str(hit.entity.get("source")),
                    entity_id=str(hit.entity.get("entity_id")),
                    text=str(hit.entity.get("text")),
                    score=max(0.0, min(1.0, float(hit.score))),
                )
            )
        return evidence
    finally:
        connections.disconnect("default")
