from pymilvus import Collection, connections

from app.core.config import Settings
from app.schemas.qa import QaEvidence
from app.services.embedding_service import embed_text
from app.services.rerank_service import rerank_evidence


def search_doc_chunks(settings: Settings, query: str, top_k: int = 5) -> list[QaEvidence]:
    """从 Milvus 召回候选片段，再通过 rerank 返回 Top-K 文本证据。"""
    connections.connect(host=settings.milvus_host, port=str(settings.milvus_port))
    try:
        collection = Collection(settings.milvus_collection)
        collection.load()
        # 先多召回候选，再交给 rerank 精排，避免向量相似度一次排序漏掉好证据。
        candidate_limit = min(max(top_k * 6, top_k), 50)
        results = collection.search(
            data=[embed_text(settings, query)],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {}},
            limit=candidate_limit,
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
        return rerank_evidence(settings, query, evidence, top_k)
    finally:
        connections.disconnect("default")
