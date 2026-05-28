import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from common import ROOT


RAW_DIR = ROOT / "data" / "raw"
SAMPLES_DIR = ROOT / "data" / "samples"
OUTPUT_FILENAMES = ("entities.json", "relations.json", "doc_chunks.json")


def normalize_id(value: str) -> str:
    return value.strip()


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-").lower()
    return slug or "item"


def read_json_records(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("records", "items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    raise ValueError(f"{path} 不是支持的 JSON 结构，根节点应为数组或包含 records/items/data 数组")


def read_csv_records(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return [dict(row) for row in csv.DictReader(file)]


def load_raw_records(raw_dir: Path, include_examples: bool = False) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(raw_dir.glob("*")):
        if path.name.startswith("."):
            continue
        if path.name.endswith(".example.json") and not include_examples:
            continue
        if path.suffix.lower() == ".json":
            records.extend(read_json_records(path))
        elif path.suffix.lower() == ".csv":
            records.extend(read_csv_records(path))
    return records


def split_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in re.split(r"[;,，；]", str(value)) if item.strip()]


def build_relation_items(record: dict[str, Any]) -> list[dict[str, str]]:
    relations = record.get("relations")
    if isinstance(relations, list):
        return [item for item in relations if isinstance(item, dict) and item.get("relation") and item.get("target")]

    # CSV 简化格式：relation=HAS_WEAKNESS，targets=CWE-78;CWE-94。
    relation = str(record.get("relation", "")).strip()
    if relation:
        return [{"relation": relation, "target": target} for target in split_values(record.get("targets") or record.get("target"))]

    return []


def add_entity(entities: dict[str, dict[str, str]], entity: dict[str, Any]) -> None:
    entity_id = normalize_id(str(entity.get("id", "")))
    if not entity_id:
        return
    entities[entity_id] = {
        "id": entity_id,
        "name": str(entity.get("name") or entity_id).strip(),
        "type": str(entity.get("type") or "Unknown").strip(),
        "description": str(entity.get("description") or "").strip(),
    }


def build_samples(records: list[dict[str, Any]]) -> tuple[list[dict], list[dict], list[dict]]:
    entities: dict[str, dict[str, str]] = {}
    relations: set[tuple[str, str, str]] = set()
    doc_chunks: dict[str, dict[str, Any]] = {}

    for index, record in enumerate(records, start=1):
        source_id = normalize_id(str(record.get("id", "")))
        if not source_id:
            continue

        add_entity(entities, record)

        text = str(record.get("text") or record.get("description") or "").strip()
        if text:
            chunk_id = str(record.get("chunk_id") or f"raw-{slugify(source_id)}-{index:03d}")
            doc_chunks[chunk_id] = {
                "chunk_id": chunk_id,
                "entity_id": source_id,
                "entity_type": str(record.get("type") or "Unknown").strip(),
                "source": str(record.get("source") or "raw").strip(),
                "text": text,
                "score": float(record.get("score") or 0.7),
            }

        for relation_item in build_relation_items(record):
            target_id = normalize_id(str(relation_item.get("target", "")))
            relation_name = str(relation_item.get("relation", "")).strip()
            if not target_id or not relation_name:
                continue

            relations.add((source_id, relation_name, target_id))
            if target_id not in entities:
                add_entity(
                    entities,
                    {
                        "id": target_id,
                        "name": relation_item.get("target_name") or target_id,
                        "type": relation_item.get("target_type") or "Unknown",
                        "description": relation_item.get("target_description") or "",
                    },
                )

    entity_rows = sorted(entities.values(), key=lambda item: (item["type"], item["id"]))
    relation_rows = [
        {"source": source, "relation": relation, "target": target}
        for source, relation, target in sorted(relations)
    ]
    chunk_rows = sorted(doc_chunks.values(), key=lambda item: item["chunk_id"])
    return entity_rows, relation_rows, chunk_rows


def write_json(path: Path, rows: list[dict], overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} 已存在；如需覆盖请加 --overwrite")
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(rows, file, ensure_ascii=False, indent=2)
        file.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="把 data/raw 中的 JSON/CSV 原始数据转换为 samples 三类 JSON。")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR, help="原始数据目录，默认 data/raw")
    parser.add_argument("--output-dir", type=Path, default=SAMPLES_DIR, help="输出目录，默认 data/samples")
    parser.add_argument("--overwrite", action="store_true", help="允许覆盖已存在的 entities/relations/doc_chunks JSON")
    parser.add_argument("--dry-run", action="store_true", help="只统计转换结果，不写文件")
    parser.add_argument("--include-examples", action="store_true", help="把 data/raw/*.example.json 也纳入转换，主要用于演示")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_raw_records(args.raw_dir, include_examples=args.include_examples)
    if not records:
        print(f"{args.raw_dir} 中没有可转换的 .json 或 .csv 原始数据。")
        print("可参考 data/raw/security_records.example.json 的字段格式。")
        return

    entities, relations, doc_chunks = build_samples(records)
    print(f"raw records: {len(records)}")
    print(f"entities: {len(entities)}")
    print(f"relations: {len(relations)}")
    print(f"doc_chunks: {len(doc_chunks)}")

    if args.dry_run:
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for filename, rows in zip(OUTPUT_FILENAMES, (entities, relations, doc_chunks), strict=True):
        write_json(args.output_dir / filename, rows, args.overwrite)
    print(f"已输出到 {args.output_dir}")


if __name__ == "__main__":
    main()
