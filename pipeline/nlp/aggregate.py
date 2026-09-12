"""L3 Opinion Aggregation with Time Decay & Severity Weights."""
import math
from datetime import datetime
from typing import Dict, List, Tuple

from pipeline.nlp.classify import ClassificationResult
from pipeline.nlp.collect import RawOpinionDoc

# Severity weights by topic
TOPIC_SEVERITY_WEIGHTS = {
    "不當管教/體罰": 1.00,
    "師資流動/人力不足": 0.85,
    "餐食與衛生": 0.80,
    "設施安全": 0.75,
    "收費爭議": 0.60,
    "行政與立案": 0.50,
    "無特定風險/一般討論": 0.05,
}


def calculate_age_days(date_str: str) -> float:
    """Calculate age in days from YYYY-MM-DD to now."""
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        delta = (datetime.now() - dt).total_seconds() / 86400.0
        return max(delta, 0.0)
    except Exception:
        return 30.0  # default 1 month if date parse fails


class OpinionAggregator:
    """Aggregates classified documents into composite opinion risk score."""

    def aggregate(
        self,
        inst_id: str,
        inst_name: str,
        classified_docs: List[Tuple[RawOpinionDoc, ClassificationResult]],
    ) -> Dict:
        """Aggregate opinion data into final metrics matching OpinionResponse schema."""
        if not classified_docs:
            return {
                "inst_id": inst_id,
                "inst_name": inst_name,
                "opinion_risk": 0.0,
                "coverage": 0,
                "has_opinion": False,
                "topic_distribution": {},
                "documents": [],
            }

        topic_distribution: Dict[str, int] = {}
        weighted_risk_sum = 0.0
        total_weight = 0.0
        formatted_documents = []

        for raw_doc, res in classified_docs:
            topic = res.topic
            topic_distribution[topic] = topic_distribution.get(topic, 0) + 1

            # Exponential decay: half-life of ~1 year (365 days)
            age_days = calculate_age_days(raw_doc.published_date)
            time_decay = math.exp(-age_days / 365.0)

            # Topic weight
            t_weight = TOPIC_SEVERITY_WEIGHTS.get(topic, 0.2)

            # Document risk impact
            if res.polarity < 0:
                # Negative sentiment amplifies risk
                negativity = abs(res.polarity)
                doc_risk = res.severity_score * negativity * t_weight * 100.0
            else:
                # Neutral or slightly positive mentions have minimal risk
                doc_risk = res.severity_score * t_weight * 10.0

            weighted_risk_sum += doc_risk * time_decay
            total_weight += time_decay

            formatted_documents.append(
                {
                    "id": raw_doc.id,
                    "source": raw_doc.source,
                    "title": raw_doc.title,
                    "url": raw_doc.url,
                    "published_date": raw_doc.published_date,
                    "topic": res.topic,
                    "polarity": round(res.polarity, 2),
                    "snippet": res.summary_zh or raw_doc.snippet[:120],
                }
            )

        coverage = len(classified_docs)
        raw_final_score = (weighted_risk_sum / total_weight) if total_weight > 0 else 0.0

        # Cap score between 0 and 100
        opinion_risk = round(min(max(raw_final_score, 0.0), 100.0), 1)

        return {
            "inst_id": inst_id,
            "inst_name": inst_name,
            "opinion_risk": opinion_risk,
            "coverage": coverage,
            "has_opinion": coverage > 0,
            "topic_distribution": topic_distribution,
            "documents": formatted_documents,
        }
