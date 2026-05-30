import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
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
HIGH_VALUE_CVE_IDS = [
    "CVE-2017-0144",
    "CVE-2017-5638",
    "CVE-2018-13379",
    "CVE-2019-0708",
    "CVE-2019-19781",
    "CVE-2020-0796",
    "CVE-2020-1472",
    "CVE-2021-26855",
    "CVE-2021-26857",
    "CVE-2021-27065",
    "CVE-2021-34473",
    "CVE-2021-34527",
    "CVE-2021-44228",
    "CVE-2022-0847",
    "CVE-2022-1388",
    "CVE-2022-22965",
    "CVE-2022-26134",
    "CVE-2022-30190",
    "CVE-2022-40684",
    "CVE-2023-0669",
    "CVE-2023-20198",
    "CVE-2023-20273",
    "CVE-2023-22515",
    "CVE-2023-22518",
    "CVE-2023-23397",
    "CVE-2023-27350",
    "CVE-2023-27997",
    "CVE-2023-2868",
    "CVE-2023-34362",
    "CVE-2023-35078",
    "CVE-2023-3519",
    "CVE-2023-36884",
    "CVE-2023-38831",
    "CVE-2023-42793",
    "CVE-2023-46805",
    "CVE-2023-49103",
    "CVE-2024-1709",
    "CVE-2024-21412",
    "CVE-2024-21887",
    "CVE-2024-23897",
    "CVE-2024-24919",
    "CVE-2024-27198",
    "CVE-2024-30051",
    "CVE-2024-30103",
    "CVE-2024-3094",
    "CVE-2024-3400",
    "CVE-2024-4577",
    "CVE-2024-6387",
    "CVE-2024-38063",
    "CVE-2024-38077",
]

NVD_CVE_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
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


def fetch_nvd_cves(cve_ids: list[str], api_key: str = "") -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"cveIds": ",".join(cve_ids)})
    headers = {"User-Agent": "CyberKG-RAG/0.1"}
    if api_key:
        headers["apiKey"] = api_key
    payload = request_json(f"{NVD_CVE_API}?{query}", headers=headers)
    vulnerabilities = payload.get("vulnerabilities") or []
    return [item for item in vulnerabilities if isinstance(item, dict)]


def fetch_nvd_cves_in_batches(cve_ids: list[str], api_key: str = "", batch_size: int = 100) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for start in range(0, len(cve_ids), batch_size):
        batch = cve_ids[start : start + batch_size]
        items.extend(fetch_nvd_cves(batch, api_key=api_key))
        print(f"fetched NVD batch {start + 1}-{start + len(batch)}")
    return items


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _nvd_datetime(value: date, end_of_day: bool = False) -> str:
    suffix = "23:59:59.999Z" if end_of_day else "00:00:00.000Z"
    return f"{value.isoformat()}T{suffix}"


def fetch_nvd_window_records(
    *,
    pub_start: str,
    pub_end: str,
    max_results: int,
    severity: str,
    api_key: str = "",
    window_days: int = 100,
) -> list[dict[str, Any]]:
    start = _parse_date(pub_start)
    end = _parse_date(pub_end)
    headers = {"User-Agent": "CyberKG-RAG/0.1"}
    if api_key:
        headers["apiKey"] = api_key

    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    current = start
    while current <= end and len(records) < max_results:
        window_end = min(current + timedelta(days=window_days - 1), end)
        query = urllib.parse.urlencode(
            {
                "pubStartDate": _nvd_datetime(current),
                "pubEndDate": _nvd_datetime(window_end, end_of_day=True),
                "cvssV3Severity": severity.upper(),
                "resultsPerPage": min(2000, max_results),
                "startIndex": 0,
                "noRejected": "",
            }
        )
        payload = request_json(f"{NVD_CVE_API}?{query}", headers=headers)
        vulnerabilities = payload.get("vulnerabilities") or []
        for item in vulnerabilities:
            cve_id = str(item.get("cve", {}).get("id") or "")
            if cve_id and cve_id not in seen:
                records.append(nvd_item_to_raw_record(cve_id, item))
                seen.add(cve_id)
            if len(records) >= max_results:
                break
        print(f"fetched NVD {severity.upper()} window {current} to {window_end}: total {len(records)}")
        current = window_end + timedelta(days=1)
    return records


def fetch_cisa_kev_records(limit: int) -> tuple[list[str], list[dict[str, Any]]]:
    payload = request_json(CISA_KEV_URL, headers={"User-Agent": "CyberKG-RAG/0.1"})
    vulnerabilities = payload.get("vulnerabilities") or []
    cve_ids: list[str] = []
    records: list[dict[str, Any]] = []

    for item in vulnerabilities[:limit]:
        cve_id = str(item.get("cveID") or "").strip().upper()
        if not cve_id:
            continue
        cve_ids.append(cve_id)
        vendor = str(item.get("vendorProject") or "").strip()
        product = str(item.get("product") or "").strip()
        name = str(item.get("vulnerabilityName") or cve_id).strip()
        description = str(item.get("shortDescription") or "").strip()
        required_action = str(item.get("requiredAction") or "").strip()
        date_added = str(item.get("dateAdded") or "").strip()
        text = description
        if required_action:
            text = f"{description} Required action: {required_action}"
        if date_added:
            text = f"{text} CISA KEV date added: {date_added}."

        relations = [
            {
                "relation": "LISTED_IN_CISA_KEV",
                "target": "CISA-KEV",
                "target_name": "CISA Known Exploited Vulnerabilities Catalog",
                "target_type": "Catalog",
                "target_description": "CISA 维护的已知被利用漏洞目录。",
            }
        ]
        if product:
            product_id = f"PROD-{vendor}-{product}".upper().replace(" ", "-")[:120]
            relations.append(
                {
                    "relation": "AFFECTS_PRODUCT",
                    "target": product_id,
                    "target_name": f"{vendor} {product}".strip(),
                    "target_type": "Product",
                    "target_description": f"CISA KEV 记录中的受影响产品：{vendor} {product}。",
                }
            )

        records.append(
            {
                "id": cve_id,
                "name": name,
                "type": "Vulnerability",
                "description": description,
                "source": "CISA KEV",
                "chunk_id": f"cisa-kev-{cve_id.lower()}",
                "text": text,
                "score": 0.9,
                "relations": relations,
            }
        )
    return list(dict.fromkeys(cve_ids)), records


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
    if len(cve_ids) > 1:
        items = fetch_nvd_cves_in_batches(cve_ids, api_key=api_key)
        item_by_id = {
            str(item.get("cve", {}).get("id")): item
            for item in items
            if item.get("cve", {}).get("id")
        }
        records = []
        for cve_id in cve_ids:
            item = item_by_id.get(cve_id)
            if item:
                records.append(nvd_item_to_raw_record(cve_id, item))
                print(f"fetched {cve_id}")
            else:
                print(f"missing {cve_id}")
        return records

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
    parser.add_argument("--high-value-50", action="store_true", help="使用内置 50 条高价值 CVE 清单")
    parser.add_argument("--cisa-kev", action="store_true", help="从 CISA KEV 目录选取真实已知被利用 CVE")
    parser.add_argument("--kev-limit", type=int, default=200, help="CISA KEV 选取数量，默认 200")
    parser.add_argument("--nvd-window", action="store_true", help="按发布时间窗口从 NVD 拉取 CVE")
    parser.add_argument("--pub-start", default="2023-01-01", help="NVD 窗口起始发布日期 YYYY-MM-DD")
    parser.add_argument("--pub-end", default="2024-12-31", help="NVD 窗口结束发布日期 YYYY-MM-DD")
    parser.add_argument("--max-results", type=int, default=200, help="NVD 窗口最多拉取数量")
    parser.add_argument("--cvss-severity", default="CRITICAL", help="NVD CVSS v3 严重级别，如 CRITICAL/HIGH")
    parser.add_argument("--nvd-api-key", default="", help="NVD API Key，可选；不传时会自动放慢请求")
    parser.add_argument("--delay", type=float, default=6.0, help="NVD 请求间隔秒数，无 API Key 时建议 >= 6")
    parser.add_argument("--download-attack", action="store_true", help="下载 MITRE ATT&CK Enterprise STIX JSON 原始文件")
    parser.add_argument("--download-cwe", action="store_true", help="下载 MITRE CWE XML ZIP 原始文件")
    parser.add_argument("--download-capec", action="store_true", help="下载 MITRE CAPEC XML ZIP 原始文件")
    return parser.parse_args()


def load_cve_ids(args: argparse.Namespace) -> list[str]:
    cve_ids = [item.strip().upper() for item in args.cve if item.strip()]
    if args.high_value_50:
        cve_ids.extend(HIGH_VALUE_CVE_IDS)
    if args.cve_file:
        cve_ids.extend(
            line.strip().upper()
            for line in args.cve_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
    if not cve_ids:
        return DEFAULT_CVE_IDS
    return list(dict.fromkeys(cve_ids))


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    cve_ids = load_cve_ids(args)
    if args.cisa_kev:
        kev_cve_ids, kev_records = fetch_cisa_kev_records(args.kev_limit)
        cve_ids.extend(kev_cve_ids)
        cisa_output = args.output_dir / "cisa_kev_records.json"
        cisa_output.write_text(json.dumps(kev_records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {cisa_output}")
    cve_ids = list(dict.fromkeys(cve_ids))

    if args.nvd_window:
        records = fetch_nvd_window_records(
            pub_start=args.pub_start,
            pub_end=args.pub_end,
            max_results=args.max_results,
            severity=args.cvss_severity,
            api_key=args.nvd_api_key,
        )
    else:
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
