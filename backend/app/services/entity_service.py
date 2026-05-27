from dataclasses import dataclass
import re

from sqlalchemy import text

from app.core.config import Settings
from app.db.postgres import create_postgres_engine


@dataclass(frozen=True)
class EntityMatch:
    """问题中识别出的实体。"""

    id: str
    name: str
    type: str
    description: str
    score: int


ALIAS_TO_ENTITY_ID = {
    "log4shell": "CVE-2021-44228",
    "log4j": "CVE-2021-44228",
    "spring4shell": "CVE-2022-22965",
    "spring": "CVE-2022-22965",
    "struts2": "CVE-2017-5638",
    "s2-045": "CVE-2017-5638",
    "proxyshell": "CVE-2021-34473",
    "exchange": "CVE-2021-34473",
    "fortigate": "CVE-2018-13379",
    "moveit": "CVE-2023-34362",
    "f5": "CVE-2022-1388",
    "big-ip": "CVE-2022-1388",
    "smbghost": "CVE-2020-0796",
    "sql注入": "CWE-89",
    "sql 注入": "CWE-89",
    "xss": "CWE-79",
    "跨站脚本": "CWE-79",
    "路径遍历": "CWE-22",
    "命令注入": "CWE-78",
    "反序列化": "CWE-502",
    "认证绕过": "CWE-287",
    "webshell": "T1505.003",
    "web shell": "T1505.003",
}


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def _load_entities(settings: Settings) -> list[dict]:
    engine = create_postgres_engine(settings)
    try:
        with engine.connect() as connection:
            rows = connection.execute(text("SELECT id, name, type, description FROM entities")).mappings()
            return [dict(row) for row in rows]
    finally:
        engine.dispose()


def identify_entity(settings: Settings, question: str) -> EntityMatch | None:
    """基于实体 id、名称和常见别名识别问题中的核心实体。"""
    normalized_question = _normalize(question)
    try:
        entities = _load_entities(settings)
    except Exception:
        return None

    by_id = {str(item["id"]): item for item in entities}
    candidates: list[EntityMatch] = []

    for alias, entity_id in ALIAS_TO_ENTITY_ID.items():
        if alias in normalized_question and entity_id in by_id:
            entity = by_id[entity_id]
            candidates.append(
                EntityMatch(
                    id=str(entity["id"]),
                    name=str(entity["name"]),
                    type=str(entity["type"]),
                    description=str(entity["description"]),
                    score=120 + len(alias),
                )
            )

    for entity in entities:
        entity_id = str(entity["id"])
        name = str(entity["name"])
        normalized_id = _normalize(entity_id)
        normalized_name = _normalize(name)
        if normalized_id and normalized_id in normalized_question:
            candidates.append(
                EntityMatch(
                    id=entity_id,
                    name=name,
                    type=str(entity["type"]),
                    description=str(entity["description"]),
                    score=100 + len(normalized_id),
                )
            )
        if normalized_name and normalized_name in normalized_question:
            candidates.append(
                EntityMatch(
                    id=entity_id,
                    name=name,
                    type=str(entity["type"]),
                    description=str(entity["description"]),
                    score=90 + len(normalized_name),
                )
            )

    if not candidates:
        return None
    return max(candidates, key=lambda item: item.score)
