from pymilvus import Collection, connections

from app.core.config import Settings
from app.schemas.qa import QaEvidence
from app.services.embedding_service import embed_text


COLLECTION_NAME = "cyber_doc_chunks"


def search_doc_chunks(settings: Settings, query: str, top_k: int = 3) -> list[QaEvidence]:
    """从 Milvus 检索和问题最相似的文本片段。"""
    connections.connect(host=settings.milvus_host, port=str(settings.milvus_port))
    try:
        collection = Collection(COLLECTION_NAME)
        collection.load()
        results = collection.search(
            data=[embed_text(settings, query)],
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
