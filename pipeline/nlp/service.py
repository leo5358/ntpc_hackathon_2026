"""Opinion analysis end-to-end service combining collection, matching, Bedrock classification, and aggregation."""
import argparse
import json
import logging
from typing import Dict, List, Optional

from pipeline.nlp.aggregate import OpinionAggregator
from pipeline.nlp.classify import BedrockOpinionClassifier
from pipeline.nlp.collect import crawl_institution_opinions
from pipeline.nlp.match import EntityMatcher, extract_core_name

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pipeline.nlp.service")


class OpinionAnalysisPipeline:
    """Orchestrates end-to-end opinion scraping, Bedrock inference, and score aggregation."""

    def __init__(self):
        self.classifier = BedrockOpinionClassifier()
        self.aggregator = OpinionAggregator()

    def run_for_institution(
        self,
        inst_id: str,
        inst_name: str,
        district: Optional[str] = None,
        max_docs_to_classify: int = 6,
    ) -> Dict:
        """Collects opinions, filters by entity matcher, classifies via Bedrock, and calculates score."""
        core_name = extract_core_name(inst_name)
        matcher = EntityMatcher(
            [
                {
                    "id": inst_id,
                    "name": inst_name,
                    "district": district or "",
                }
            ]
        )

        # 1. Crawl raw opinions from multiple sources (Google News, PTT, Dcard, Threads)
        raw_docs = crawl_institution_opinions(
            inst_name=inst_name,
            aliases=[f"{core_name}幼兒園", f"{core_name}非營利"],
            core_name=core_name,
        )

        # 2. Match and filter relevant documents
        matched_pairs = []
        for doc in raw_docs:
            combined = f"{doc.title} {doc.raw_content or doc.snippet}"
            matched, conf, terms = matcher.match_document(combined, inst_id)
            if matched:
                matched_pairs.append(doc)

        logger.info("Found %d matched documents out of %d crawled for %s", len(matched_pairs), len(raw_docs), inst_name)

        # 3. Classify with AWS Bedrock Claude (or rule fallback)
        classified_results = []
        for doc in matched_pairs[:max_docs_to_classify]:
            text_to_analyze = doc.raw_content if doc.raw_content else doc.snippet
            res = self.classifier.classify_single(
                doc_id=doc.id,
                title=doc.title,
                snippet=text_to_analyze,
                inst_name=inst_name,
            )
            classified_results.append((doc, res))

        # 4. Aggregate metrics and risk score
        return self.aggregator.aggregate(inst_id=inst_id, inst_name=inst_name, classified_docs=classified_results)


def main():
    parser = argparse.ArgumentParser(description="Test Opinion Scraping and Bedrock Analysis")
    parser.add_argument("--id", default="N07", help="Institution ID")
    parser.add_argument("--name", default="新北市北大非營利幼兒園", help="Institution Name")
    parser.add_argument("--district", default="三峽區", help="District")
    args = parser.parse_args()

    pipeline = OpinionAnalysisPipeline()
    result = pipeline.run_for_institution(inst_id=args.id, inst_name=args.name, district=args.district)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
