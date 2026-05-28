import argparse
import sys
from dataclasses import dataclass
from time import perf_counter
from typing import Callable

from fastapi.testclient import TestClient
from sqlalchemy import text

from common import BACKEND_DIR  # noqa: F401 - 导入 common 会把 backend 加入 sys.path
from app.core.config import get_settings
from app.db.postgres import create_postgres_engine
from app.main import app


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str
    elapsed_ms: int


def elapsed_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)


def run_check(name: str, fn: Callable[[], str]) -> CheckResult:
    started_at = perf_counter()
    try:
        message = fn()
        return CheckResult(name=name, ok=True, message=message, elapsed_ms=elapsed_ms(started_at))
    except Exception as exc:  # noqa: BLE001 - 健康检查脚本要汇总所有失败项
        return CheckResult(name=name, ok=False, message=str(exc), elapsed_ms=elapsed_ms(started_at))


def assert_response_ok(response, path: str) -> dict:
    if response.status_code != 200:
        raise AssertionError(f"{path} HTTP {response.status_code}: {response.text[:300]}")
    payload = response.json()
    if payload.get("success") is False:
        raise AssertionError(f"{path} success=false: {payload.get('message')}")
    return payload


def check_dependencies(client: TestClient) -> str:
    payload = assert_response_ok(client.get("/health/dependencies"), "/health/dependencies")
    data = payload.get("data") or []
    failed = [item for item in data if item.get("status") != "ok"]
    if failed:
        raise AssertionError(f"依赖异常：{failed}")
    return ", ".join(f"{item['name']}=ok" for item in data)


def check_postgres_tables() -> str:
    settings = get_settings()
    engine = create_postgres_engine(settings)
    try:
        with engine.connect() as connection:
            counts = {
                table: int(connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())
                for table in ("entities", "relations", "doc_chunks")
            }
    finally:
        engine.dispose()

    empty_tables = [table for table, count in counts.items() if count <= 0]
    if empty_tables:
        raise AssertionError(f"PostgreSQL 表为空：{empty_tables}")
    return ", ".join(f"{table}={count}" for table, count in counts.items())


def check_overview(client: TestClient) -> str:
    payload = assert_response_ok(client.get("/api/overview/summary"), "/api/overview/summary")
    metrics = payload.get("data", {}).get("metrics", [])
    metric_map = {item.get("key"): item.get("value") for item in metrics}
    required = ("entities", "relations", "documents", "graph_nodes", "graph_relations", "vectors")
    missing = [key for key in required if not metric_map.get(key)]
    if missing:
        raise AssertionError(f"总览指标缺失或为 0：{missing}")
    return ", ".join(f"{key}={metric_map[key]}" for key in required)


def check_graph(client: TestClient) -> str:
    payload = assert_response_ok(
        client.get("/api/graph/neighbors", params={"entity_id": "CVE-2021-44228", "depth": 2}),
        "/api/graph/neighbors",
    )
    data = payload.get("data", {})
    node_count = len(data.get("nodes") or [])
    edge_count = len(data.get("edges") or [])
    if node_count <= 0 or edge_count <= 0:
        raise AssertionError(f"图谱查询为空：nodes={node_count}, edges={edge_count}")
    return f"nodes={node_count}, edges={edge_count}"


def check_search(client: TestClient) -> str:
    payload = assert_response_ok(
        client.get("/api/search/docs", params={"query": "Log4Shell 防护", "top_k": 5}),
        "/api/search/docs",
    )
    data = payload.get("data") or []
    if not data:
        raise AssertionError("Milvus 文本检索没有召回结果")
    return f"evidence={len(data)}"


def check_qa(client: TestClient) -> str:
    payload = assert_response_ok(
        client.post("/api/qa/ask", json={"question": "Log4Shell 漏洞的攻击原理和防护措施是什么？"}),
        "/api/qa/ask",
    )
    data = payload.get("data", {})
    path_count = len(data.get("graph_paths") or [])
    evidence_count = len(data.get("text_evidence") or [])
    if path_count <= 0 or evidence_count <= 0:
        raise AssertionError(f"KG-RAG 证据不足：paths={path_count}, evidence={evidence_count}")
    return f"confidence={data.get('confidence')}, paths={path_count}, evidence={evidence_count}"


def check_qa_comparison(client: TestClient) -> str:
    payload = assert_response_ok(
        client.post("/api/experiments/qa-comparison", json={"question": "Log4Shell 漏洞如何被利用，如何缓解？"}),
        "/api/experiments/qa-comparison",
    )
    results = payload.get("data", {}).get("results") or []
    modes = {item.get("mode") for item in results}
    required = {"普通 LLM", "普通 RAG", "KG-RAG"}
    if modes != required:
        raise AssertionError(f"问答对比模式不完整：{modes}")
    return ", ".join(f"{item['mode']}={item['confidence']}" for item in results)


def check_kg_completion(client: TestClient) -> str:
    summary = assert_response_ok(client.get("/api/experiments/kg-completion"), "/api/experiments/kg-completion")
    dataset = summary.get("data", {}).get("dataset", {})
    if dataset.get("entity_count", 0) <= 0 or dataset.get("triple_count", 0) <= 0:
        raise AssertionError(f"知识补全数据集为空：{dataset}")

    prediction = assert_response_ok(
        client.post(
            "/api/experiments/kg-completion/predict",
            json={"head": "CVE-2021-44228", "relation": "HAS_WEAKNESS", "top_k": 3},
        ),
        "/api/experiments/kg-completion/predict",
    )
    predictions = prediction.get("data", {}).get("predictions") or []
    if not predictions:
        raise AssertionError("知识补全 Top-K 预测为空")
    return f"triples={dataset.get('triple_count')}, predictions={len(predictions)}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查 CyberKG-RAG 项目的三库、核心接口和实验接口是否健康。")
    parser.add_argument("--quick", action="store_true", help="快速检查：跳过 DeepSeek 问答和问答对比实验")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = TestClient(app)
    checks: list[tuple[str, Callable[[], str]]] = [
        ("三库依赖连通", lambda: check_dependencies(client)),
        ("PostgreSQL 表数据", check_postgres_tables),
        ("系统总览接口", lambda: check_overview(client)),
        ("Neo4j 图谱查询", lambda: check_graph(client)),
        ("Milvus 文本检索", lambda: check_search(client)),
        ("知识补全实验", lambda: check_kg_completion(client)),
    ]
    if not args.quick:
        checks.extend(
            [
                ("KG-RAG 智能问答", lambda: check_qa(client)),
                ("问答对比实验", lambda: check_qa_comparison(client)),
            ]
        )

    results = [run_check(name, fn) for name, fn in checks]
    print("\nCyberKG-RAG 项目健康检查")
    print("=" * 80)
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.name} ({result.elapsed_ms}ms)")
        print(f"       {result.message}")

    failed = [result for result in results if not result.ok]
    print("=" * 80)
    if failed:
        print(f"检查失败：{len(failed)} 项")
        return 1
    print("全部检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
