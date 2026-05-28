import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from common import ROOT


RAW_DIR = ROOT / "data" / "raw"
DEFAULT_CVE_IDS = [
    "CVE-2021-44228",
    "CVE-2022-22965",
    "CVE-2017-5638",
    "CVE-2023-34362",
    "CVE-2022-1388",
]

NVD_CVE_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
ATTACK_ENTERPRISE_STIX_URL = (
    "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json"
)
CWE_XML_ZIP_URL = "https://cwe.mitre.org/data/xml/cwec_latest.xml.zip"
CAPEC_XML_ZIP_URL = "https://capec.mitre.org/data/xml/capec_latest.xml.zip"


def request_json(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - URL 来自脚本内置官方数据源
        return json.loads(response.read().decode("utf-8"))


def download_file(url: str, output_path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "CyberKG-RAG/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310 - URL 来自脚本内置官方数据源
        output_path.write_bytes(response.read())


def first_english_description(cve_item: dict[str, Any]) -> str:
    descriptions = cve_item.get("cve", {}).get("descriptions", [])
    for item in descriptions:
        if item.get("lang") == "en":
            return str(item.get("value") or "").strip()
    return ""


def cwe_relations(cve_item: dict[str, Any]) -> list[dict[str, str]]:
    relations: list[dict[str, str]] = []
    weaknesses = cve_item.get("cve", {}).get("weaknesses", [])
    for weakness in weaknesses:
        for description in weakness.get("description", []):
            value = str(description.get("value") or "").strip()
            if value.startswith("CWE-") and value != "CWE-noinfo":
                relations.append(
                    {
                        "relation": "HAS_WEAKNESS",
                        "target": value,
                        "target_name": value,
                        "target_type": "Weakness",
                        "target_description": f"NVD 记录中关联的弱点 {value}。",
                    }
                )
    return relations


def affected_products(cve_item: dict[str, Any]) -> list[dict[str, str]]:
    products: list[dict[str, str]] = []
    configurations = cve_item.get("cve", {}).get("configurations", [])
    seen: set[str] = set()
    for configuration in configurations:
        for node in configuration.get("nodes", []):
            for cpe_match in node.get("cpeMatch", []):
                criteria = str(cpe_match.get("criteria") or "")
                parts = criteria.split(":")
                if len(parts) < 6:
                    continue
                vendor = parts[3].replace("_", " ")
                product = parts[4].replace("_", " ")
                product_id = f"PROD-{vendor}-{product}".upper().replace(" ", "-")[:120]
                if product_id in seen:
                    continue
                seen.add(product_id)
                products.append(
                    {
                        "relation": "AFFECTS_PRODUCT",
                        "target": product_id,
                        "target_name": f"{vendor} {product}".strip(),
                        "target_type": "Product",
                        "target_description": f"NVD CPE 中提取的受影响产品：{vendor} {product}。",
                    }
                )
                if len(products) >= 3:
                    return products
    return products


def cvss_score(cve_item: dict[str, Any]) -> float:
    metrics = cve_item.get("cve", {}).get("metrics", {})
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        values = metrics.get(key)
        if values:
            score = values[0].get("cvssData", {}).get("baseScore")
            if score is not None:
                return min(1.0, float(score) / 10.0)
    return 0.7


def fetch_nvd_cve(cve_id: str, api_key: str = "") -> dict[str, Any] | None:
    query = urllib.parse.urlencode({"cveId": cve_id})
    headers = {"User-Agent": "CyberKG-RAG/0.1"}
    if api_key:
        headers["apiKey"] = api_key
    payload = request_json(f"{NVD_CVE_API}?{query}", headers=headers)
    vulnerabilities = payload.get("vulnerabilities") or []
    return vulnerabilities[0] if vulnerabilities else None


def nvd_item_to_raw_record(cve_id: str, item: dict[str, Any]) -> dict[str, Any]:
    description = first_english_description(item)
    relations = cwe_relations(item)
    relations.extend(affected_products(item))
    return {
        "id": cve_id,
        "name": cve_id,
        "type": "Vulnerability",
        "description": description,
        "source": "NVD",
        "text": description,
        "score": cvss_score(item),
        "relations": relations,
    }


def fetch_nvd_records(cve_ids: list[str], api_key: str = "", delay: float = 6.0) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, cve_id in enumerate(cve_ids):
        item = fetch_nvd_cve(cve_id, api_key=api_key)
        if item:
            records.append(nvd_item_to_raw_record(cve_id, item))
            print(f"fetched {cve_id}")
        else:
            print(f"missing {cve_id}")
        if index < len(cve_ids) - 1:
            time.sleep(delay)
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从公开安全数据源下载 raw 数据，供 build_samples_from_raw.py 转换。")
    parser.add_argument("--output-dir", type=Path, default=RAW_DIR, help="输出目录，默认 data/raw")
    parser.add_argument("--cve", action="append", default=[], help="指定 CVE ID，可重复传入")
    parser.add_argument("--cve-file", type=Path, help="每行一个 CVE ID")
    parser.add_argument("--nvd-api-key", default="", help="NVD API Key，可选；不传时会自动放慢请求")
    parser.add_argument("--delay", type=float, default=6.0, help="NVD 请求间隔秒数，无 API Key 时建议 >= 6")
    parser.add_argument("--download-attack", action="store_true", help="下载 MITRE ATT&CK Enterprise STIX JSON 原始文件")
    parser.add_argument("--download-cwe", action="store_true", help="下载 MITRE CWE XML ZIP 原始文件")
    parser.add_argument("--download-capec", action="store_true", help="下载 MITRE CAPEC XML ZIP 原始文件")
    return parser.parse_args()


def load_cve_ids(args: argparse.Namespace) -> list[str]:
    cve_ids = [item.strip().upper() for item in args.cve if item.strip()]
    if args.cve_file:
        cve_ids.extend(
            line.strip().upper()
            for line in args.cve_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
    return cve_ids or DEFAULT_CVE_IDS


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    cve_ids = load_cve_ids(args)
    records = fetch_nvd_records(cve_ids, api_key=args.nvd_api_key, delay=args.delay)
    nvd_output = args.output_dir / "nvd_cve_records.json"
    nvd_output.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {nvd_output}")

    if args.download_attack:
        output = args.output_dir / "mitre_attack_enterprise.json"
        download_file(ATTACK_ENTERPRISE_STIX_URL, output)
        print(f"wrote {output}")

    if args.download_cwe:
        output = args.output_dir / "cwe_latest.xml.zip"
        download_file(CWE_XML_ZIP_URL, output)
        print(f"wrote {output}")

    if args.download_capec:
        output = args.output_dir / "capec_latest.xml.zip"
        download_file(CAPEC_XML_ZIP_URL, output)
        print(f"wrote {output}")


if __name__ == "__main__":
    main()
