import json
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
