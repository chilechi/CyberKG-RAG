import argparse
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import text

from common import BACKEND_DIR  # noqa: F401 - 导入 common 会把 backend 加入 sys.path
from app.core.config import get_settings
from app.db.postgres import create_postgres_engine


DEFAULT_CENTER_ENTITY = "CVE-2021-44228"


def safe_filename(value: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", value).strip(" .") or "untitled"


def canvas_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def yaml_escape(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def wikilink(entity_id: str, display: str | None = None) -> str:
    label = display or entity_id
    return f"[[entities/{safe_filename(entity_id)}|{label}]]"


def load_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    settings = get_settings()
    engine = create_postgres_engine(settings)
    try:
        with engine.connect() as connection:
            entities = [dict(row) for row in connection.execute(text("SELECT id, name, type, description FROM entities")).mappings()]
            relations = [dict(row) for row in connection.execute(text("SELECT source, relation, target FROM relations")).mappings()]
            chunks = [
                dict(row)
                for row in connection.execute(
                    text("SELECT chunk_id, entity_id, source, score, text FROM doc_chunks ORDER BY chunk_id")
                ).mappings()
            ]
            return entities, relations, chunks
    finally:
        engine.dispose()


def build_note(
    entity: dict[str, Any],
    outgoing: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    entity_by_id: dict[str, dict[str, Any]],
) -> str:
    entity_id = str(entity["id"])
    lines = [
        "---",
        f"id: {yaml_escape(entity_id)}",
        f"title: {yaml_escape(str(entity.get('name') or entity_id))}",
        f"type: {yaml_escape(str(entity.get('type') or 'Unknown'))}",
        "tags:",
        "  - cyberkg/entity",
        f"  - cyberkg/type/{str(entity.get('type') or 'Unknown').lower()}",
        "---",
        "",
        f"# {entity.get('name') or entity_id}",
        "",
        f"- ID: `{entity_id}`",
        f"- 类型: `{entity.get('type') or 'Unknown'}`",
        "",
        "## 描述",
        "",
        str(entity.get("description") or "暂无描述。"),
        "",
        "## 出向关系",
        "",
    ]

    if outgoing:
        for item in sorted(outgoing, key=lambda row: (row["relation"], row["target"])):
            target = entity_by_id.get(item["target"], {"name": item["target"]})
            lines.append(f"- `{item['relation']}` -> {wikilink(item['target'], target.get('name'))}")
    else:
        lines.append("- 暂无")

    lines.extend(["", "## 入向关系", ""])
    if incoming:
        for item in sorted(incoming, key=lambda row: (row["relation"], row["source"])):
            source = entity_by_id.get(item["source"], {"name": item["source"]})
            lines.append(f"- {wikilink(item['source'], source.get('name'))} -> `{item['relation']}`")
    else:
        lines.append("- 暂无")

    lines.extend(["", "## 文本证据", ""])
    if chunks:
        for chunk in chunks:
            lines.append(f"### {chunk['source']} / {chunk['chunk_id']}")
            lines.append("")
            lines.append(f"- 分数: `{chunk['score']}`")
            lines.append("")
            lines.append(str(chunk["text"]))
            lines.append("")
    else:
        lines.append("暂无文本证据。")

    lines.append("")
    return "\n".join(lines)


def write_entity_notes(vault: Path, entities: list[dict], relations: list[dict], chunks: list[dict]) -> None:
    entity_dir = vault / "entities"
    entity_dir.mkdir(parents=True, exist_ok=True)

    entity_by_id = {item["id"]: item for item in entities}
    outgoing = defaultdict(list)
    incoming = defaultdict(list)
    chunks_by_entity = defaultdict(list)
    for relation in relations:
        outgoing[relation["source"]].append(relation)
        incoming[relation["target"]].append(relation)
    for chunk in chunks:
        chunks_by_entity[chunk["entity_id"]].append(chunk)

    for entity in entities:
        note = build_note(
            entity,
            outgoing[entity["id"]],
            incoming[entity["id"]],
            chunks_by_entity[entity["id"]],
            entity_by_id,
        )
        (entity_dir / f"{safe_filename(entity['id'])}.md").write_text(note, encoding="utf-8", newline="\n")


def write_index(vault: Path, entities: list[dict], relations: list[dict], chunks: list[dict]) -> None:
    by_type = defaultdict(list)
    for entity in entities:
        by_type[entity.get("type") or "Unknown"].append(entity)

    lines = [
        "---",
        "title: CyberKG 索引",
        "tags:",
        "  - cyberkg/index",
        "---",
        "",
        "# CyberKG 索引",
        "",
        f"- 实体数: `{len(entities)}`",
        f"- 关系数: `{len(relations)}`",
        f"- 文档片段数: `{len(chunks)}`",
        "",
        "## 常用入口",
        "",
        f"- {wikilink(DEFAULT_CENTER_ENTITY, 'Log4Shell / CVE-2021-44228')}",
        "- [[canvases/log4shell|Log4Shell 局部图谱 Canvas]]",
        "",
        "## 按类型浏览",
        "",
    ]
    for entity_type, items in sorted(by_type.items()):
        lines.append(f"### {entity_type}")
        lines.append("")
        for entity in sorted(items, key=lambda item: item["id"]):
            lines.append(f"- {wikilink(entity['id'], entity.get('name') or entity['id'])}")
        lines.append("")

    (vault / "CyberKG 索引.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def local_relations(center: str, relations: list[dict], depth: int) -> list[dict]:
    selected: list[dict] = []
    frontier = {center}
    visited = {center}
    for _ in range(depth):
        next_frontier = set()
        for relation in relations:
            if relation["source"] in frontier or relation["target"] in frontier:
                selected.append(relation)
                if relation["source"] not in visited:
                    next_frontier.add(relation["source"])
                if relation["target"] not in visited:
                    next_frontier.add(relation["target"])
        visited.update(next_frontier)
        frontier = next_frontier
    unique = {(item["source"], item["relation"], item["target"]): item for item in selected}
    return list(unique.values())


def write_canvas(vault: Path, center: str, entities: list[dict], relations: list[dict], depth: int) -> None:
    canvas_dir = vault / "canvases"
    canvas_dir.mkdir(parents=True, exist_ok=True)

    entity_by_id = {item["id"]: item for item in entities}
    selected_relations = local_relations(center, relations, depth)
    node_ids = sorted({center} | {item["source"] for item in selected_relations} | {item["target"] for item in selected_relations})

    nodes = []
    center_node_id = canvas_id(f"node:{center}")
    nodes.append(
        {
            "id": center_node_id,
            "type": "file",
            "x": 0,
            "y": 0,
            "width": 300,
            "height": 180,
            "file": f"entities/{safe_filename(center)}.md",
            "color": "1",
        }
    )

    others = [item for item in node_ids if item != center]
    radius = 420
    for index, entity_id in enumerate(others):
        angle = (2 * math.pi * index) / max(1, len(others))
        x = int(math.cos(angle) * radius)
        y = int(math.sin(angle) * radius)
        entity = entity_by_id.get(entity_id, {})
        color = {"Weakness": "6", "AttackPattern": "2", "Technique": "5", "Mitigation": "4", "Product": "3"}.get(
            entity.get("type"),
            "5",
        )
        nodes.append(
            {
                "id": canvas_id(f"node:{entity_id}"),
                "type": "file",
                "x": x,
                "y": y,
                "width": 280,
                "height": 160,
                "file": f"entities/{safe_filename(entity_id)}.md",
                "color": color,
            }
        )

    edges = [
        {
            "id": canvas_id(f"edge:{item['source']}:{item['relation']}:{item['target']}"),
            "fromNode": canvas_id(f"node:{item['source']}"),
            "fromSide": "right",
            "toNode": canvas_id(f"node:{item['target']}"),
            "toSide": "left",
            "toEnd": "arrow",
            "label": item["relation"],
        }
        for item in selected_relations
        if item["source"] in node_ids and item["target"] in node_ids
    ]

    canvas = {"nodes": nodes, "edges": edges}
    (canvas_dir / "log4shell.canvas").write_text(json.dumps(canvas, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="把 PostgreSQL 中的知识图谱导出为 Obsidian 笔记和 Canvas。")
    parser.add_argument("--vault", type=Path, required=True, help="Obsidian vault 路径")
    parser.add_argument("--center", default=DEFAULT_CENTER_ENTITY, help="局部 Canvas 的中心实体 ID")
    parser.add_argument("--depth", type=int, default=1, choices=[1, 2], help="Canvas 展示深度")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.vault.mkdir(parents=True, exist_ok=True)
    entities, relations, chunks = load_rows()
    write_entity_notes(args.vault, entities, relations, chunks)
    write_index(args.vault, entities, relations, chunks)
    write_canvas(args.vault, args.center, entities, relations, args.depth)
    print(f"exported entities={len(entities)}, relations={len(relations)}, chunks={len(chunks)} to {args.vault}")


if __name__ == "__main__":
    main()
