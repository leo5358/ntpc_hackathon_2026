"""Public opinion analysis route connecting crawler and AWS Bedrock inference."""
import logging
from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from api.schemas import OpinionResponse
from pipeline.nlp.service import OpinionAnalysisPipeline

logger = logging.getLogger("api.routes.opinion")
router = APIRouter(prefix="/api/opinion", tags=["opinion"])

pipeline = OpinionAnalysisPipeline()

# Standard test institution mappings for quick lookup
SAMPLE_ROSTER = {
    "N07": {"name": "新北市北大非營利幼兒園", "district": "三峽區"},
    "N09": {"name": "新北市安興非營利幼兒園", "district": "新店區"},
    "N11": {"name": "新北市新林非營利幼兒園", "district": "林口區"},
    "N12": {"name": "新北市昌福非營利幼兒園", "district": "鶯歌區"},
    "N15": {"name": "新北市新月非營利幼兒園", "district": "板橋區"},
}


class DirectAnalyzeRequest(BaseModel):
    name: str
    inst_id: Optional[str] = "custom"
    district: Optional[str] = None


@router.get("/{inst_id}", response_model=OpinionResponse)
async def get_institution_opinion(
    inst_id: str,
    crawl: bool = Query(False, description="Whether to trigger live web crawl and Bedrock analysis"),
):
    """Return sentiment and topic classification details for institution.

    If crawl=True, triggers live crawler and AWS Bedrock model inference.
    """
    inst_info = SAMPLE_ROSTER.get(inst_id, {"name": f"幼兒園-{inst_id}", "district": ""})
    name = inst_info["name"]
    district = inst_info.get("district")

    if crawl:
        try:
            logger.info("Executing live crawl and Bedrock scoring for %s (%s)", name, inst_id)
            result = pipeline.run_for_institution(inst_id=inst_id, inst_name=name, district=district)
            return OpinionResponse(**result)
        except Exception as e:
            logger.error("Error running opinion pipeline: %s", e)

    # Return default empty/cached response
    return OpinionResponse(
        inst_id=inst_id,
        inst_name=name,
        opinion_risk=0.0,
        coverage=0,
        has_opinion=False,
        topic_distribution={},
        documents=[],
    )


@router.post("/analyze", response_model=OpinionResponse)
async def analyze_custom_institution(req: DirectAnalyzeRequest):
    """Live trigger crawler and Bedrock scoring for arbitrary institution name."""
    logger.info("Live analyzing custom institution: %s", req.name)
    result = pipeline.run_for_institution(
        inst_id=req.inst_id or "custom",
        inst_name=req.name,
        district=req.district,
    )
    return OpinionResponse(**result)
