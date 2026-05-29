import re

from neo4j import GraphDatabase

from common import read_sample_json
from app.core.config import get_settings


RELATION_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


def safe_relation_type(relation: str) -> str:
    """Neo4j 关系类型不能参数化，这里只允许大写字母、数字和下划线。"""
    if not RELATION_PATTERN.fullmatch(relation):
        raise ValueError(f"Invalid relation type: {relation}")
    return relation


def main() -> None:
    settings = get_settings()
    entities = read_sample_json("entities.json")
    relations = read_sample_json("relations.json")
    driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))

    with driver.session() as session:
        session.run("CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE")
        # 导入脚本按 samples 重建课程样例图谱，避免旧节点和旧关系残留影响统计与查询。
        session.run("MATCH (:Entity)-[r]->(:Entity) DELETE r")
        session.run("MATCH (e:Entity) DELETE e")

        for entity in entities:
            session.run(
                """
                MERGE (e:Entity {id: $id})
                SET e.name = $name,
                    e.type = $type,
                    e.description = $description
                """,
                **entity,
            )

        for relation in relations:
            relation_type = safe_relation_type(relation["relation"])
            session.run(
                f"""
                MATCH (source:Entity {{id: $source}})
                MATCH (target:Entity {{id: $target}})
                MERGE (source)-[r:{relation_type}]->(target)
                SET r.relation = $relation
                """,
                **relation,
            )

    driver.close()
    print(f"Neo4j import done: {len(entities)} entities, {len(relations)} relations")


if __name__ == "__main__":
    main()
