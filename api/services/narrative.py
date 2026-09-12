"""全市綜整報告之敘述文字生成（AWS Bedrock Claude，失敗自動退回規則模板）。

統計數字一律由呼叫端（前端 cityReport.ts）算好後傳入，本模組只負責把數字寫成
可簽陳的中文敘述；模型不得自行推算或杜撰任何數值與園名。

Bedrock client 的憑證解析沿用 pipeline/nlp/classify.py 的兩段式做法
（具名 Profile -> 預設憑證鏈），確保與輿情分類模組行為一致。
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional

import boto3
from dotenv import load_dotenv

from api.config import load_config

logger = logging.getLogger("api.services.narrative")

load_dotenv()

DEFAULT_BEDROCK_MODEL = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")


def _init_bedrock_client(region: Optional[str] = None, profile_name: Optional[str] = None):
    """建立 bedrock-runtime client；任何失敗都回 None 讓呼叫端退回模板。"""
    cfg = load_config()
    aws_cfg = cfg.get("aws", {})
    target_region = (
        region
        or os.getenv("AWS_DEFAULT_REGION")
        or os.getenv("AWS_REGION")
        or aws_cfg.get("region", "us-west-2")
    )
    target_profile = profile_name or os.getenv("AWS_PROFILE") or aws_cfg.get("profile_name", "workshop")

    # Attempt 1: Named profile (e.g. workshop)
    try:
        session = boto3.Session(profile_name=target_profile, region_name=target_region)
        client = session.client("bedrock-runtime", region_name=target_region)
        logger.info("Narrative Bedrock client via profile '%s' in '%s'", target_profile, target_region)
        return client
    except Exception as e1:
        logger.debug("Profile '%s' unavailable: %s", target_profile, e1)

    # Attempt 2: Environment variables or default credentials chain
    try:
        session = boto3.Session(region_name=target_region)
        client = session.client("bedrock-runtime", region_name=target_region)
        logger.info("Narrative Bedrock client via default credential chain in '%s'", target_region)
        return client
    except Exception as e2:
        logger.warning("Bedrock client unavailable (%s); narrative falls back to template.", e2)
        return None


def _build_prompt(stats: Dict[str, Any]) -> str:
    """組出提示詞：只准依據傳入數字敘述，不得推論違法事實。"""
    return f"""你是協助臺灣地方政府教育局撰寫年度風險評估報告的稽核幕僚。
請依據下列「已算好的統計數字」撰寫報告的執行摘要、關鍵發現與稽查建議。

【統計數據（JSON）】
{json.dumps(stats, ensure_ascii=False, indent=2)}

【撰寫規則（務必遵守）】
1. 只能引用上述 JSON 中出現的數字與園名，**嚴禁自行推算、外插或杜撰任何未提供的數值、園名、行政區或事件**。
2. 風險分數為模型推估之相對異常指標，**不得敘述為違法事實、不得指控任何機構違法**，請使用「風險偏高」「建議優先查核」等行政用語。
3. 語氣為公文書面體，繁體中文，不使用 Markdown 標題或條列符號。
4. 執行摘要 3 至 5 句，需涵蓋受評家數、整體風險水準、最需關注之群組或行政區。
5. 關鍵發現 3 條，每條 40 字以內，須各自對應一項具體統計數字。
6. 稽查建議 3 條，每條 50 字以內，需具體可執行（如查核順序、跨機關會辦、資料補正）。
7. 若統計中顯示輿情涵蓋率偏低，請在摘要或建議中提醒該項限制。

你必須只輸出一個標準 JSON 物件，不要輸出任何其他文字或 Markdown 標記：
{{
  "executive_summary": "3 至 5 句的執行摘要",
  "key_findings": ["發現1", "發現2", "發現3"],
  "recommendations": ["建議1", "建議2", "建議3"]
}}
"""


def _template_narrative(stats: Dict[str, Any]) -> Dict[str, Any]:
    """規則模板：不呼叫任何外部服務，離線可重現。"""
    total = stats.get("total_institutions", 0)
    avg = stats.get("average_score", 0.0)
    high = stats.get("high_risk_count", 0)
    penalties = stats.get("total_penalties", 0)
    groups: List[Dict[str, Any]] = stats.get("peer_groups", [])
    districts: List[Dict[str, Any]] = stats.get("top_districts", [])
    opinion_coverage = stats.get("opinion_coverage")

    top_group = max(groups, key=lambda g: g.get("average_score", 0.0)) if groups else None
    top_district = districts[0] if districts else None

    summary_parts = [
        f"本年度共納入 {total} 所幼兒園進行風險評估，整體平均風險分數為 {avg:.1f} 分。",
        f"其中風險分數達 60 分以上之高風險機構計 {high} 所，歷史裁罰紀錄合計 {penalties} 件。",
    ]
    if top_group:
        summary_parts.append(
            f"以同儕群組觀察，{top_group.get('peer_group')} 平均風險分數 "
            f"{top_group.get('average_score', 0.0):.1f} 分，為各群組中最高，建議列為本年度查核重點。"
        )
    if top_district:
        summary_parts.append(
            f"地理分布上以{top_district.get('district')}平均 "
            f"{top_district.get('average_score', 0.0):.1f} 分最高，可優先安排實地查核。"
        )

    findings = [
        f"高風險機構 {high} 所，占受評總數 {high / total * 100:.1f}%。" if total else "尚無受評機構資料。",
        f"歷史裁罰合計 {penalties} 件，顯示既有改善措施仍待追蹤。",
    ]
    if top_group:
        findings.append(
            f"{top_group.get('peer_group')} 平均 {top_group.get('average_score', 0.0):.1f} 分，"
            f"最高 {top_group.get('max_score', 0.0):.1f} 分。"
        )

    recommendations = [
        "風險分數 60 分以上機構應依風險判斷基準列為不可容忍風險，由管理階層督導研擬改善計畫並提供資源。",
        "同一行政區之高風險機構建議合併排程實地查核，以節省有限稽查人力。",
    ]
    if opinion_coverage is not None and opinion_coverage < 0.5:
        recommendations.append(
            f"目前輿情資料涵蓋率僅 {opinion_coverage * 100:.0f}%，判讀時應併同書面查核結果，避免以輿情有無逕行推論。"
        )
    else:
        recommendations.append("建議每季更新決算與裁罰資料，維持風險評分之時效性。")

    return {
        "executive_summary": "".join(summary_parts),
        "key_findings": findings[:3],
        "recommendations": recommendations[:3],
        "generated_by": "template",
        "model_id": None,
    }


def generate_city_narrative(
    stats: Dict[str, Any],
    *,
    use_bedrock: bool = True,
    model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """產生全市綜整報告之敘述文字。

    Args:
        stats: 前端算好的統計摘要。
        use_bedrock: 為 False 時直接使用規則模板（供離線 Demo 與測試）。
        model_id: 覆寫 Bedrock 模型（預設取自 BEDROCK_MODEL_ID）。

    Returns:
        executive_summary / key_findings / recommendations / generated_by / model_id。
        generated_by 為 "bedrock" 或 "template"，供前端標示文字來源。
    """
    if not use_bedrock:
        return _template_narrative(stats)

    target_model = model_id or DEFAULT_BEDROCK_MODEL
    client = _init_bedrock_client()
    if client is None:
        return _template_narrative(stats)

    try:
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": _build_prompt(stats)}],
        }
        response = client.invoke_model(
            modelId=target_model,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )
        output_text = json.loads(response["body"].read().decode("utf-8"))["content"][0]["text"].strip()

        # 與 classify.py 相同的 Markdown 圍籬清理
        if "```json" in output_text:
            output_text = output_text.split("```json")[1].split("```")[0].strip()
        elif "```" in output_text:
            output_text = output_text.split("```")[1].split("```")[0].strip()

        parsed = json.loads(output_text)
        summary = str(parsed.get("executive_summary", "")).strip()
        if not summary:
            raise ValueError("Bedrock returned empty executive_summary")

        return {
            "executive_summary": summary,
            "key_findings": [str(x) for x in parsed.get("key_findings", [])][:5],
            "recommendations": [str(x) for x in parsed.get("recommendations", [])][:5],
            "generated_by": "bedrock",
            "model_id": target_model,
        }
    except Exception as e:
        logger.warning("Bedrock narrative failed (%s). Falling back to template.", e)
        return _template_narrative(stats)
