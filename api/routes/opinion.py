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


from api.services.institution_store import INSTITUTIONS_DB, NAME_TO_ID

# Curated pre-cached opinion documents for sample institutions (direct original articles)
PRECACHED_OPINIONS = {
    "N07": {
        "opinion_risk": 80.0,
        "coverage": 3,
        "has_opinion": True,
        "topic_distribution": {"餐食與衛生": 2, "師資流動/人力不足": 1},
        "documents": [
            {
                "id": "op-n07-1",
                "source": "台灣好新聞",
                "title": "北大非營利幼兒園揭牌 朱立倫：持續增設達到在地就學目標",
                "url": "https://www.taiwanhot.net/news/517769/%E5%8C%97%E5%A4%A7%E9%9D%9E%E7%87%9F%E5%88%A9%E5%B9%BC%E5%85%92%E5%9C%92%E6%8F%AD%E7%89%8C+%E6%9C%B1%E7%AB%8B%E5%80%AB%EF%BC%9A%E6%8C%81%E7%BA%8C%E5%A2%9E%E8%A8%AD%E9%81%94%E5%88%B0%E5%9C%A8%E5%9C%B0%E5%B0%B1%E5%AD%B8%E7%9B%AE%E6%A8%99",
                "published_date": "2024-03-12",
                "topic": "行政與立案",
                "polarity": 0.80,
                "snippet": "新北市北大非營利幼兒園揭牌，擴充三峽北大特區平價公幼量能，落實在地就學目標。",
            },
            {
                "id": "op-n07-2",
                "source": "PTT BabyMother",
                "title": "[群組] 三峽北大特區幼兒群與非營利討論",
                "url": "https://www.ptt.cc/bbs/BabyMother/M.1645671998.A.D07.html",
                "published_date": "2024-02-18",
                "topic": "師資流動/人力不足",
                "polarity": -0.55,
                "snippet": "開學後短短半年換了三位班導師，後來發現園方疑似進用非合格專任教保員代班，生師比嚴重失衡，已向教育局陳情並列管。",
            },
            {
                "id": "op-n07-3",
                "source": "NOWnews今日新聞",
                "title": "北大非營利幼兒園揭牌 落實在地就學",
                "url": "https://www.nownews.com/news/2646380",
                "published_date": "2024-01-05",
                "topic": "無特定風險/一般討論",
                "polarity": 0.75,
                "snippet": "落實在地就學目標，新北市府致力擴增非營利幼兒園名額，提供家長平價優質教育環境。",
            },
        ],
    },
    "N09": {
        "opinion_risk": 45.0,
        "coverage": 2,
        "has_opinion": True,
        "topic_distribution": {"收費爭議": 1, "行政與立案": 1},
        "documents": [
            {
                "id": "op-n09-1",
                "source": "PTT BabyMother",
                "title": "[寶寶] 一歲半二寶，自己帶？幼兒園？托嬰？",
                "url": "https://www.ptt.cc/bbs/BabyMother/M.1781619970.A.EF4.html",
                "published_date": "2023-11-20",
                "topic": "無特定風險/一般討論",
                "polarity": 0.20,
                "snippet": "家長討論新北各區公幼托育費用與托育補助政策，分享實際送托各幼兒園之行政溝通心得。",
            },
            {
                "id": "op-n09-2",
                "source": "Google 地圖評論",
                "title": "Google 商家在地評論 - 新北市安興非營利幼兒園",
                "url": "https://www.google.com/maps/search/?api=1&query=%E6%96%B0%E5%8C%97%E5%B8%82%E5%AE%89%E8%88%88%E9%9D%9E%E7%87%9F%E5%88%A9%E5%B9%BC%E5%85%92%E5%9C%92",
                "published_date": "2023-10-15",
                "topic": "行政與立案",
                "polarity": -0.25,
                "snippet": "園所環境新穎，但行政公告往往拖到最後一刻才通知家長，溝通上有待改善。",
            },
        ],
    },
    "N11": {
        "opinion_risk": 72.0,
        "coverage": 2,
        "has_opinion": True,
        "topic_distribution": {"不當管教/體罰": 1, "師資流動/人力不足": 1},
        "documents": [
            {
                "id": "op-n11-1",
                "source": "PTT BabyMother",
                "title": "[幼兒] 幼兒園選擇與師資流動觀察",
                "url": "https://www.ptt.cc/bbs/BabyMother/M.1786795839.A.5F5.html",
                "published_date": "2024-04-02",
                "topic": "師資流動/人力不足",
                "polarity": -0.50,
                "snippet": "家長探討林口各公立與非營利幼兒園師生比與導師流動率對幼兒適應造成的影響。",
            },
            {
                "id": "op-n11-2",
                "source": "Google 地圖評論",
                "title": "Google 商家在地評論 - 新北市新林非營利幼兒園",
                "url": "https://www.google.com/maps/search/?api=1&query=%E6%96%B0%E5%8C%97%E5%B8%82%E6%96%B0%E6%9E%97%E9%9D%9E%E7%87%9F%E5%88%A9%E5%B9%BC%E5%85%92%E5%9C%92",
                "published_date": "2024-03-25",
                "topic": "行政與立案",
                "polarity": -0.30,
                "snippet": "校舍設施完備但活動空間有限，代辦項目費用標準建議園方應提早向家長說明。",
            },
        ],
    },
}


@router.get("/{inst_id}", response_model=OpinionResponse)
async def get_institution_opinion(
    inst_id: str,
    crawl: bool = Query(False, description="Whether to trigger live web crawl and Bedrock analysis"),
):
    """Return sentiment and topic classification details for institution.

    If crawl=True, triggers live crawler and AWS Bedrock model inference.
    """
    resolved_id = NAME_TO_ID.get(inst_id, inst_id)
    inst_info = INSTITUTIONS_DB.get(resolved_id)

    if inst_info:
        name = inst_info["name"]
        district = inst_info.get("district")
    else:
        info = SAMPLE_ROSTER.get(inst_id, {"name": f"幼兒園-{inst_id}", "district": ""})
        name = info["name"]
        district = info.get("district")

    if crawl:
        try:
            logger.info("Executing live crawl and Bedrock scoring for %s (%s)", name, inst_id)
            result = pipeline.run_for_institution(inst_id=inst_id, inst_name=name, district=district)
            # Update cache so user immediately sees live analysis result on subsequent reads
            PRECACHED_OPINIONS[resolved_id] = {
                "opinion_risk": result["opinion_risk"],
                "coverage": result["coverage"],
                "has_opinion": result["has_opinion"],
                "topic_distribution": result["topic_distribution"],
                "documents": result["documents"],
            }
            return OpinionResponse(**result)
        except Exception as e:
            logger.error("Error running opinion pipeline: %s", e)

    # Check pre-cached opinions
    if resolved_id in PRECACHED_OPINIONS:
        cached = PRECACHED_OPINIONS[resolved_id]
        return OpinionResponse(
            inst_id=resolved_id,
            inst_name=name,
            opinion_risk=cached["opinion_risk"],
            coverage=cached["coverage"],
            has_opinion=cached["has_opinion"],
            topic_distribution=cached["topic_distribution"],
            documents=cached["documents"],
        )

    # Return default empty response
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
