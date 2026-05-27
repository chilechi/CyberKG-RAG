import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
SAMPLES_DIR = ROOT / "data" / "samples"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def read_sample_json(filename: str) -> list[dict[str, Any]]:
    with (SAMPLES_DIR / filename).open("r", encoding="utf-8") as file:
        return json.load(file)


def mock_embedding(text: str, dim: int = 64) -> list[float]:
    """生成确定性 mock 向量，先验证 Milvus 入库链路，后续替换为真实 embedding。"""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < dim:
        for byte in digest:
            values.append((byte / 255.0) * 2.0 - 1.0)
            if len(values) == dim:
                break
        digest = hashlib.sha256(digest).digest()

    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]
