import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from common import ROOT

from app.core.config import get_settings
from app.schemas.comparison import QaComparisonResponse, QaComparisonResult
from app.services.comparison_service import run_qa_comparison


DEFAULT_DATASET = ROOT / "data" / "eval" / "qa_eval.json"
DEFAULT_OUTPUT_DIR = ROOT / "experiments" / "qa_eval"


def _read_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def _normalize(value: str) -> str:
    return value.casefold().replace(" ", "")


def _hit_rate(expected: list[str], observed: set[str]) -> float:
    if not expected:
        return 1.0
    normalized_observed = {_normalize(item) for item in observed}
    hit_count = sum(1 for item in expected if _normalize(item) in normalized_observed)
    return round(hit_count / len(expected), 4)


def _keyword_coverage(expected_keywords: list[str], text: str) -> float:
    if not expected_keywords:
        return 1.0
    normalized_text = _normalize(text)
    hit_count = sum(1 for keyword in expected_keywords if _normalize(keyword) in normalized_text)
    return round(hit_count / len(expected_keywords), 4)


def _collect_observed_entities(result: QaComparisonResult, expected_entities: list[str]) -> set[str]:
    observed: set[str] = set()

    for path in result.graph_paths:
        for item in path:
            if _looks_like_relation(item):
                continue
            observed.add(item)

    for evidence in result.text_evidence:
        observed.add(evidence.entity_id)

    # 大模型答案里可能直接写出实体编号，但不一定出现在结构化证据字段里，所以这里补一次文本命中。
    normalized_answer = _normalize(result.answer)
    for entity_id in expected_entities:
        if _normalize(entity_id) in normalized_answer:
            observed.add(entity_id)

    return observed


def _looks_like_relation(value: str) -> bool:
    return value.isupper() and "_" in value


def _collect_observed_relations(result: QaComparisonResult) -> set[str]:
    observed: set[str] = set()
    for path in result.graph_paths:
        # 图谱路径按 source -> relation -> target 组织，长度不固定时只取中间的关系位置。
        for index in range(1, len(path), 2):
            observed.add(path[index])
    return observed


def _score_result(case: dict[str, Any], result: QaComparisonResult) -> dict[str, Any]:
    expected_entities = case.get("expected_entities", [])
    expected_relations = case.get("expected_relations", [])
    expected_keywords = case.get("expected_keywords", [])

    observed_entities = _collect_observed_entities(result, expected_entities)
    observed_relations = _collect_observed_relations(result)
    evidence_count = result.graph_path_count + result.text_evidence_count

    entity_hit_rate = _hit_rate(expected_entities, observed_entities)
    relation_hit_rate = _hit_rate(expected_relations, observed_relations)
    keyword_coverage = _keyword_coverage(expected_keywords, result.answer)
    evidence_score = min(1.0, evidence_count / 8)
    final_score = round(
        keyword_coverage * 0.4
        + entity_hit_rate * 0.25
        + relation_hit_rate * 0.2
        + evidence_score * 0.15,
        4,
    )

    return {
        "mode": result.mode,
        "final_score": final_score,
        "entity_hit_rate": entity_hit_rate,
        "relation_hit_rate": relation_hit_rate,
        "keyword_coverage": keyword_coverage,
        "evidence_score": round(evidence_score, 4),
        "confidence": result.confidence,
        "elapsed_ms": result.elapsed_ms,
        "graph_path_count": result.graph_path_count,
        "text_evidence_count": result.text_evidence_count,
        "observed_entities": sorted(observed_entities),
        "observed_relations": sorted(observed_relations),
        "answer": result.answer,
    }


def _summarize(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in case_results:
        for result in case["results"]:
            grouped[result["mode"]].append(result)

    mode_summary = {}
    for mode, results in grouped.items():
        mode_summary[mode] = {
            "avg_final_score": round(statistics.mean(item["final_score"] for item in results), 4),
            "avg_entity_hit_rate": round(statistics.mean(item["entity_hit_rate"] for item in results), 4),
            "avg_relation_hit_rate": round(statistics.mean(item["relation_hit_rate"] for item in results), 4),
            "avg_keyword_coverage": round(statistics.mean(item["keyword_coverage"] for item in results), 4),
            "avg_evidence_score": round(statistics.mean(item["evidence_score"] for item in results), 4),
            "avg_confidence": round(statistics.mean(item["confidence"] for item in results), 4),
            "avg_graph_path_count": round(statistics.mean(item["graph_path_count"] for item in results), 2),
            "avg_text_evidence_count": round(statistics.mean(item["text_evidence_count"] for item in results), 2),
            "avg_elapsed_ms": round(statistics.mean(item["elapsed_ms"] for item in results), 2),
            "case_count": len(results),
        }

    best_mode = max(mode_summary.items(), key=lambda item: item[1]["avg_final_score"])[0] if mode_summary else ""
    return {
        "case_count": len(case_results),
        "mode_summary": mode_summary,
        "best_mode": best_mode,
    }


def evaluate(dataset: list[dict[str, Any]], limit: int | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    settings = get_settings()
    selected_dataset = dataset[:limit] if limit else dataset
    case_results = []

    for index, case in enumerate(selected_dataset, start=1):
        print(f"[{index}/{len(selected_dataset)}] 评测：{case['question']}")
        response: QaComparisonResponse = run_qa_comparison(settings, case["question"])
        scores = [_score_result(case, result) for result in response.results]
        best_result = max(scores, key=lambda item: item["final_score"])
        case_results.append(
            {
                "id": case["id"],
                "question": case["question"],
                "reference_answer": case.get("reference_answer", ""),
                "expected_entities": case.get("expected_entities", []),
                "expected_relations": case.get("expected_relations", []),
                "expected_keywords": case.get("expected_keywords", []),
                "best_mode": best_result["mode"],
                "results": scores,
            }
        )

    return case_results, _summarize(case_results)


def main() -> None:
    parser = argparse.ArgumentParser(description="评测普通 LLM、普通 RAG 和 KG-RAG 的问答效果")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET, help="评测集 JSON 路径")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="评测结果输出目录")
    parser.add_argument("--limit", type=int, default=None, help="只评测前 N 条，便于快速检查")
    args = parser.parse_args()

    dataset = _read_json(args.dataset)
    results, summary = evaluate(dataset, limit=args.limit)

    _write_json(args.output_dir / "results.json", results)
    _write_json(args.output_dir / "summary.json", summary)
    print(f"评测完成：{args.output_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
