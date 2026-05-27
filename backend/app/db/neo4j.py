from neo4j import GraphDatabase

from app.core.config import Settings


def check_neo4j(settings: Settings) -> None:
    """执行最小 Cypher，确认 Neo4j Bolt 连接可用。"""
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    try:
        with driver.session() as session:
            session.run("RETURN 1 AS ok").consume()
    finally:
        driver.close()
