"""不需 AWS 的後端煙霧測試，供 CI 於每次 push/PR 執行。

    python -m infra.smoke_local

以 FastAPI TestClient 直接打應用程式，涵蓋報表與排名等主要端點；
輿情與敘述生成一律走離線模式，確保無憑證環境也能通過。
"""
import json
import logging
import sys

from fastapi.testclient import TestClient

from api.main import app

logging.basicConfig(level=logging.WARNING)

client = TestClient(app)
failures = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}{(' — ' + detail) if detail else ''}")
    else:
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")
        failures.append(name)


print("後端端點煙霧測試")

r = client.get("/api/health")
check("GET /api/health", r.status_code == 200 and r.json()["status"] == "ok")

r = client.get("/api/rankings?year=112")
check("GET /api/rankings", r.status_code == 200, f"{r.json().get('total')} 筆")

r = client.get("/api/institutions")
check("GET /api/institutions", r.status_code == 200, f"{len(r.json())} 筆")

r = client.get("/api/report/scales")
scales = r.json() if r.status_code == 200 else {}
check(
    "GET /api/report/scales",
    r.status_code == 200 and len(scales.get("matrix", [])) == 9 and scales.get("tolerance_threshold") == 4,
    "附件2/3/4 級距完整",
)

r = client.get("/api/report/N07?academic_year=112&demo=true")
report = r.json() if r.status_code == 200 else {}
check(
    "GET /api/report/{id}（demo）",
    r.status_code == 200 and len(report.get("rows", [])) > 0 and report["meta"]["is_sample"] is True,
    f"{len(report.get('rows', []))} 列",
)

# 風險值必須符合附件三 R = L x I
rows_ok = all(
    row["existing"]["risk_value"] == row["existing"]["likelihood"] * row["existing"]["impact"]
    for row in report.get("rows", [])
)
check("附件七風險值 R = L × I", rows_ok)

r = client.post(
    "/api/report/build",
    json={
        "inst_id": "TEST",
        "inst_name": "測試幼兒園",
        "academic_year": 112,
        "signals": [{"code": "UNDERSTAFFING", "composite_score": 78.5, "penalty_count": 2}],
    },
)
built = r.json() if r.status_code == 200 else {}
check(
    "POST /api/report/build",
    r.status_code == 200 and len(built.get("rows", [])) == 1,
    f"R={built['rows'][0]['existing']['risk_value']}" if built.get("rows") else "",
)

r = client.post(
    "/api/report/city/narrative",
    json={
        "total_institutions": 14,
        "average_score": 45.8,
        "high_risk_count": 5,
        "total_penalties": 12,
        "peer_groups": [],
        "top_districts": [],
        "use_bedrock": False,
    },
)
narrative = r.json() if r.status_code == 200 else {}
check(
    "POST /api/report/city/narrative（模板模式）",
    r.status_code == 200
    and narrative.get("generated_by") == "template"
    and len(narrative.get("executive_summary", "")) > 20,
)

r = client.get("/api/opinion/N07")
check("GET /api/opinion/{id}（不觸發爬蟲）", r.status_code == 200)

print()
if failures:
    print(f"失敗 {len(failures)} 項：{', '.join(failures)}")
    sys.exit(1)
print("全部通過")
