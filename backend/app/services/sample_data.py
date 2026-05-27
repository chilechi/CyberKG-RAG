import json
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"


def _read_json(filename: str) -> list[dict[str, Any]]:
    path = SAMPLES_DIR / filename
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


@lru_cache
def load_entities() -> list[dict[str, Any]]:
    """读取样例实体，后续真实数据导入前先作为稳定 mock 数据源。"""
    return _read_json("entities.json")


@lru_cache
def load_relations() -> list[dict[str, Any]]:
    """读取样例关系三元组。"""
    return _read_json("relations.json")


@lru_cache
def load_doc_chunks() -> list[dict[str, Any]]:
    """读取样例文本片段，后续会替换为 Milvus 召回结果。"""
    return _read_json("doc_chunks.json")
