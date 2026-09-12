"""L1 Risk Topic Classification & L2 Polarity with AWS Bedrock Claude."""
import json
import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from api.config import load_config

logger = logging.getLogger("pipeline.nlp.classify")

# 6 Major risk categories mirroring official preschool penalty regulations
RISK_TOPICS = [
    "不當管教/體罰",
    "餐食與衛生",
    "收費爭議",
    "師資流動/人力不足",
    "設施安全",
    "行政與立案",
    "無特定風險/一般討論",
]

# Rule-based fallback keywords
TOPIC_KEYWORDS = {
    "不當管教/體罰": ["體罰", "打人", "巴頭", "虐童", "不當對待", "關廁所", "監視器", "推擠"],
    "餐食與衛生": ["過期", "發霉", "腹瀉", "食物中毒", "吃不飽", "菜色差", "衛生差", "腸病毒"],
    "收費爭議": ["超收", "巧立名目", "才藝費", "退費", "補貼爭議", "亂收費", "學費漲"],
    "師資流動/人力不足": ["師生比", "無照", "黑牌", "換老師", "離職", "缺人", "師資不穩", "超額配比"],
    "設施安全": ["遊具損壞", "逃生梯", "消防違規", "施工安全", "設備老舊", "安全門鎖"],
    "行政與立案": ["超收學生", "未立案", "隱匿班級", "分校違法", "幼托一體違規"],
}

import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_BEDROCK_MODEL = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")


@dataclass
class ClassificationResult:
    doc_id: str
    is_risk_relevant: bool
    topic: str
    topic_confidence: float
    polarity: float  # -1.0 (extremely negative) to +1.0 (positive)
    severity_score: float  # 0.0 to 1.0
    summary_zh: str
    keywords: List[str]
    model_provider: str = "aws_bedrock"


class BedrockOpinionClassifier:
    """Classifies public opinion text using AWS Bedrock Claude models with local rule fallback."""

    def __init__(
        self,
        region: Optional[str] = None,
        profile_name: Optional[str] = None,
        model_id: str = DEFAULT_BEDROCK_MODEL,
    ):
        self.region = region
        self.profile_name = profile_name
        self.model_id = model_id
        self._init_bedrock_client()

    def _init_bedrock_client(self):
        self.client = None
        cfg = load_config()
        aws_cfg = cfg.get("aws", {})
        target_region = self.region or os.getenv("AWS_DEFAULT_REGION") or os.getenv("AWS_REGION") or aws_cfg.get("region", "us-west-2")
        target_profile = self.profile_name or os.getenv("AWS_PROFILE") or aws_cfg.get("profile_name", "workshop")

        # Attempt 1: Named profile (e.g. workshop)
        try:
            session = boto3.Session(profile_name=target_profile, region_name=target_region)
            self.client = session.client("bedrock-runtime", region_name=target_region)
            logger.info("AWS Bedrock client initialized via profile '%s' in region '%s'", target_profile, target_region)
            return
        except Exception as e1:
            logger.debug("Profile '%s' not found or invalid: %s", target_profile, e1)

        # Attempt 2: Environment variables or default credentials chain
        try:
            session = boto3.Session(region_name=target_region)
            self.client = session.client("bedrock-runtime", region_name=target_region)
            logger.info("AWS Bedrock client initialized via default credential chain in region '%s'", target_region)
            return
        except Exception as e2:
            logger.warning("Failed to initialize AWS Bedrock client (%s). Will use rule-based fallback.", e2)
            self.client = None

    def _build_prompt(self, title: str, snippet: str, inst_name: str) -> str:
        return f"""你是一位專門分析臺灣幼兒園營運合規與風險的審計分析專家。請閱讀以下針對「{inst_name}」的網路輿情討論內容，並進行客觀的風險與情緒極性分析。

【文章標題】：{title}
【內容摘要】：{snippet}

請根據臺灣《幼兒教育及照顧法》標準，評估內容是否涉及以下 6 大營運風險類別之一：
1. 不當管教/體罰
2. 餐食與衛生
3. 收費爭議
4. 師資流動/人力不足
5. 設施安全
6. 行政與立案
7. 無特定風險/一般討論

你必須只輸出一個標準的 JSON 格式物件，請勿輸出任何其他 Markdown 引導字串或說明：
{{
  "is_risk_relevant": true 或 false (若為負面風險指控或爭議為 true),
  "primary_topic": "上述 7 個類別之一",
  "topic_confidence": 0.0 到 1.0 的小數,
  "sentiment_polarity": -1.0 (極度負面抱怨/控訴) 到 1.0 (極度正面推薦/讚揚) 之間的數值,
  "severity_score": 0.0 (無危害) 到 1.0 (嚴重重大違規) 之間的數值,
  "summary_zh": "繁體中文重點摘要（30字內）",
  "matched_keywords": ["關鍵詞1", "關鍵詞2"]
}}
"""

    def classify_single(self, doc_id: str, title: str, snippet: str, inst_name: str) -> ClassificationResult:
        """Classify a single opinion item using Bedrock, falling back to rule-based parser if unavailable."""
        combined_text = f"{title} {snippet}"

        if self.client:
            try:
                prompt = self._build_prompt(title, snippet, inst_name)
                payload = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 512,
                    "temperature": 0.1,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                }

                response = self.client.invoke_model(
                    modelId=self.model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(payload),
                )

                response_body = json.loads(response["body"].read().decode("utf-8"))
                output_text = response_body["content"][0]["text"].strip()

                # Extract JSON if enclosed in markdown code blocks
                if "```json" in output_text:
                    output_text = output_text.split("```json")[1].split("```")[0].strip()
                elif "```" in output_text:
                    output_text = output_text.split("```")[1].split("```")[0].strip()

                parsed = json.loads(output_text)
                return ClassificationResult(
                    doc_id=doc_id,
                    is_risk_relevant=parsed.get("is_risk_relevant", False),
                    topic=parsed.get("primary_topic", "無特定風險/一般討論"),
                    topic_confidence=float(parsed.get("topic_confidence", 0.8)),
                    polarity=float(parsed.get("sentiment_polarity", 0.0)),
                    severity_score=float(parsed.get("severity_score", 0.0)),
                    summary_zh=parsed.get("summary_zh", snippet[:60]),
                    keywords=parsed.get("matched_keywords", []),
                    model_provider="aws_bedrock_claude",
                )
            except Exception as e:
                logger.warning("Bedrock invocation failed (%s). Falling back to rule classifier.", e)

        # Fallback to rule-based keyword & lexicon matching
        return self._rule_based_fallback(doc_id, combined_text)

    def _rule_based_fallback(self, doc_id: str, text: str) -> ClassificationResult:
        """Rule-based classifier baseline when Bedrock is offline."""
        detected_topic = "無特定風險/一般討論"
        matched_kw: List[str] = []
        highest_match_count = 0

        for topic, keywords in TOPIC_KEYWORDS.items():
            hits = [k for k in keywords if k in text]
            if len(hits) > highest_match_count:
                highest_match_count = len(hits)
                detected_topic = topic
                matched_kw = hits

        is_risk = highest_match_count > 0
        polarity = -0.6 if is_risk else 0.1
        severity = min(0.3 + highest_match_count * 0.25, 0.95) if is_risk else 0.0

        return ClassificationResult(
            doc_id=doc_id,
            is_risk_relevant=is_risk,
            topic=detected_topic,
            topic_confidence=0.75 if is_risk else 0.5,
            polarity=polarity,
            severity_score=severity,
            summary_zh=f"規則分類命中: {', '.join(matched_kw)}" if matched_kw else "社群一般提及",
            keywords=matched_kw,
            model_provider="rule_lexicon_fallback",
        )
