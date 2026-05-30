import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from common import ROOT


DEFAULT_ENTITIES = ROOT / "data" / "samples" / "entities.json"
DEFAULT_RELATIONS = ROOT / "data" / "samples" / "relations.json"
DEFAULT_OUTPUT_DIR = ROOT / "experiments" / "kg_completion"


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def _write_triples(path: Path, triples: list[tuple[str, str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for head, relation, tail in triples:
            file.write(f"{head}\t{relation}\t{tail}\n")


def _read_triples(path: Path) -> list[tuple[str, str, str]]:
    triples = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            triples.append((parts[0], parts[1], parts[2]))
    return triples


def _load_triples(relations_path: Path) -> list[tuple[str, str, str]]:
    rows = _read_json(relations_path)
    triples = []
    for row in rows:
        head = str(row.get("source", "")).strip()
        relation = str(row.get("relation", "")).strip()
        tail = str(row.get("target", "")).strip()
        if head and relation and tail:
            triples.append((head, relation, tail))
    return sorted(set(triples))


def _split_triples(
    triples: list[tuple[str, str, str]],
    *,
    seed: int,
    train_ratio: float,
    valid_ratio: float,
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    shuffled = triples[:]
    random.Random(seed).shuffle(shuffled)
    train_count = int(len(shuffled) * train_ratio)
    valid_count = max(1, int(len(shuffled) * valid_ratio)) if shuffled else 0
    train = shuffled[:train_count]
    valid = shuffled[train_count : train_count + valid_count]
    test = shuffled[train_count + valid_count :]
    train, valid, test = _ensure_training_coverage(train, valid, test)
    return train, valid, test


def _ensure_training_coverage(
    train: list[tuple[str, str, str]],
    valid: list[tuple[str, str, str]],
    test: list[tuple[str, str, str]],
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    train_entities = {entity for head, _, tail in train for entity in (head, tail)}
    train_relations = {relation for _, relation, _ in train}

    def keep_or_move(rows: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
        kept = []
        for triple in rows:
            head, relation, tail = triple
            # PyKEEN 的验证/测试集必须使用训练集中已知的实体和关系。
            if head not in train_entities or tail not in train_entities or relation not in train_relations:
                train.append(triple)
                train_entities.update([head, tail])
                train_relations.add(relation)
            else:
                kept.append(triple)
        return kept

    valid = keep_or_move(valid)
    test = keep_or_move(test)
    return train, valid, test


def _dataset_summary(
    entities_path: Path,
    triples: list[tuple[str, str, str]],
    train: list[tuple[str, str, str]],
    valid: list[tuple[str, str, str]],
    test: list[tuple[str, str, str]],
) -> dict[str, Any]:
    entities = _read_json(entities_path)
    entity_types: dict[str, int] = {}
    for item in entities:
        entity_type = str(item.get("type") or "Unknown")
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1

    relation_types: dict[str, int] = {}
    for _, relation, _ in triples:
        relation_types[relation] = relation_types.get(relation, 0) + 1

    return {
        "entity_count": len(entities),
        "relation_count": len(relation_types),
        "triple_count": len(triples),
        "train_count": len(train),
        "valid_count": len(valid),
        "test_count": len(test),
        "entity_types": dict(sorted(entity_types.items())),
        "relation_types": dict(sorted(relation_types.items())),
    }


def _import_pykeen():
    try:
        import numpy as np
        from pykeen.pipeline import pipeline
        from pykeen.triples import TriplesFactory
    except ImportError as exc:
        raise SystemExit(
            "PyKEEN is not installed. Run `pip install -r backend/requirements.txt` first."
        ) from exc
    return np, pipeline, TriplesFactory


def _metric(flat_metrics: dict[str, float], preferred: str, *fallback_needles: str) -> float:
    if preferred in flat_metrics:
        return max(0.0, min(1.0, float(flat_metrics[preferred])))

    for key, value in flat_metrics.items():
        normalized = key.lower()
        if all(needle in normalized for needle in fallback_needles):
            return max(0.0, min(1.0, float(value)))
    return 0.0


def _curve_rows(model_values: dict[str, list[float]], epochs: int) -> list[dict[str, float]]:
    rows = []
    max_points = max((len(values) for values in model_values.values()), default=0)
    for index in range(max_points):
        row = {
            "epoch": index + 1 if epochs <= 0 else round((index + 1) * epochs / max_points),
            "transe": 0.0,
            "complex": 0.0,
            "rotate": 0.0,
        }
        for model, values in model_values.items():
            key = model.lower()
            if key == "complex":
                key = "complex"
            if key in row and index < len(values):
                row[key] = round(float(values[index]), 4)
        rows.append(row)
    return rows


def _constant_curve(metrics: list[dict[str, Any]], metric_name: str) -> list[dict[str, float]]:
    row = {"epoch": 1, "transe": 0.0, "complex": 0.0, "rotate": 0.0}
    for item in metrics:
        key = str(item["model"]).lower()
        if key in row:
            row[key] = float(item[metric_name])
    return [row]


def train_models(
    train_path: Path,
    valid_path: Path,
    test_path: Path,
    *,
    models: list[str],
    epochs: int,
    embedding_dim: int,
    batch_size: int,
    seed: int,
    device: str | None,
) -> tuple[list[dict[str, Any]], dict[str, list[float]]]:
    np, pipeline, TriplesFactory = _import_pykeen()
    training = TriplesFactory.from_labeled_triples(np.array(_read_triples(train_path), dtype=str))
    validation = TriplesFactory.from_labeled_triples(
        np.array(_read_triples(valid_path), dtype=str),
        entity_to_id=training.entity_to_id,
        relation_to_id=training.relation_to_id,
    )
    testing = TriplesFactory.from_labeled_triples(
        np.array(_read_triples(test_path), dtype=str),
        entity_to_id=training.entity_to_id,
        relation_to_id=training.relation_to_id,
    )

    metrics = []
    loss_by_model: dict[str, list[float]] = {}
    for model in models:
        started_at = perf_counter()
        result = pipeline(
            training=training,
            validation=validation,
            testing=testing,
            model=model,
            model_kwargs={"embedding_dim": embedding_dim},
            training_kwargs={"num_epochs": epochs, "batch_size": batch_size},
            random_seed=seed,
            device=device,
        )
        flat = result.metric_results.to_flat_dict()
        elapsed = max(1, int(perf_counter() - started_at))
        losses = [float(value) for value in getattr(result, "losses", [])]
        loss_by_model[model] = losses
        metrics.append(
            {
                "model": model,
                "mrr": round(_metric(flat, "both.realistic.inverse_harmonic_mean_rank", "realistic", "inverse_harmonic_mean_rank"), 4),
                "hits_at_1": round(_metric(flat, "both.realistic.hits_at_1", "realistic", "hits_at_1"), 4),
                "hits_at_3": round(_metric(flat, "both.realistic.hits_at_3", "realistic", "hits_at_3"), 4),
                "hits_at_10": round(_metric(flat, "both.realistic.hits_at_10", "realistic", "hits_at_10"), 4),
                "train_seconds": elapsed,
            }
        )
    return metrics, loss_by_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="使用 PyKEEN 训练知识图谱补全模型并导出实验结果。")
    parser.add_argument("--entities", type=Path, default=DEFAULT_ENTITIES, help="entities.json 路径")
    parser.add_argument("--relations", type=Path, default=DEFAULT_RELATIONS, help="relations.json 路径")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="实验输出目录")
    parser.add_argument("--models", nargs="+", default=["TransE"], help="PyKEEN 模型名，例如 TransE ComplEx RotatE")
    parser.add_argument("--epochs", type=int, default=100, help="训练轮数")
    parser.add_argument("--embedding-dim", type=int, default=64, help="实体/关系向量维度")
    parser.add_argument("--batch-size", type=int, default=128, help="训练 batch size")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--device", default=None, help="训练设备，例如 cpu 或 cuda")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    triples = _load_triples(args.relations)
    train, valid, test = _split_triples(triples, seed=args.seed, train_ratio=0.8, valid_ratio=0.1)
    dataset = _dataset_summary(args.entities, triples, train, valid, test)

    triples_dir = args.output_dir / "triples"
    _write_triples(triples_dir / "all.tsv", triples)
    _write_triples(triples_dir / "train.tsv", train)
    _write_triples(triples_dir / "valid.tsv", valid)
    _write_triples(triples_dir / "test.tsv", test)
    _write_json(args.output_dir / "dataset.json", dataset)

    metrics, loss_by_model = train_models(
        triples_dir / "train.tsv",
        triples_dir / "valid.tsv",
        triples_dir / "test.tsv",
        models=args.models,
        epochs=args.epochs,
        embedding_dim=args.embedding_dim,
        batch_size=args.batch_size,
        seed=args.seed,
        device=args.device,
    )
    best_model = max(metrics, key=lambda item: item["mrr"])["model"] if metrics else ""
    curves = {
        "mrr_curve": _constant_curve(metrics, "mrr"),
        "hits_at_10_curve": _constant_curve(metrics, "hits_at_10"),
        "loss_curve": _curve_rows(loss_by_model, args.epochs),
    }
    summary = {
        "dataset": dataset,
        "model_metrics": metrics,
        **curves,
        "conclusion": (
            f"PyKEEN 已基于当前三元组完成训练评测，最佳模型为 {best_model}。"
            "指标来自固定随机种子的 8:1:1 train/valid/test 划分。"
        ),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "models": args.models,
            "epochs": args.epochs,
            "embedding_dim": args.embedding_dim,
            "batch_size": args.batch_size,
            "seed": args.seed,
            "device": args.device,
        },
    }
    _write_json(args.output_dir / "summary.json", summary)
    print(f"PyKEEN training finished: {args.output_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
