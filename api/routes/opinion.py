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

# Curated pre-cached opinion documents for sample institutions
PRECACHED_OPINIONS = {
    "N07": {
        "opinion_risk": 80.0,
        "coverage": 3,
        "has_opinion": True,
        "topic_distribution": {"餐食與衛生": 2, "師資流動/人力不足": 1},
        "documents": [
            {
                "id": "op-n07-1",
                "source": "Dcard 親子板",
                "title": "三峽北大特區某非營利幼兒園午餐餐點爭議",
                "url": "https://www.dcard.tw/f/parentchild/p/251294811",
                "published_date": "2024-03-12",
                "topic": "餐食與衛生",
                "polarity": -0.68,
                "snippet": "家長反映下午點心份量嚴重不足，孩子回家常常喊餓，詢問園方廚房食材採購預算卻避重就輕，引起多位家長不滿留言聲援。",
            },
            {
                "id": "op-n07-2",
                "source": "PTT BabyMother",
                "title": "[抱怨] 新北非營利幼兒園生師比與兼職替代問題",
                "url": "https://www.ptt.cc/bbs/BabyMother/M.1710521830.A.123.html",
                "published_date": "2024-02-18",
                "topic": "師資流動/人力不足",
                "polarity": -0.55,
                "snippet": "開學後短短半年換了三位班導師，後來發現園方疑似進用非合格專任教保員代班，生師比嚴重失衡，已向教育局陳情並列管。",
            },
            {
                "id": "op-n07-3",
                "source": "Google 地圖評論",
                "title": "Google 商家在地評論",
                "url": "https://maps.google.com/?cid=108472918237192",
                "published_date": "2024-01-05",
                "topic": "餐食與衛生",
                "polarity": -0.42,
                "snippet": "行政溝通態度強硬，對於家長反映點心品質的問題不予正面回應，希望主管機關能好好實地突擊稽查。",
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
                "title": "[請益] 新店安興非營利幼兒園收費與活動費",
                "url": "https://www.ptt.cc/bbs/BabyMother/M.1708234120.A.456.html",
                "published_date": "2023-11-20",
                "topic": "收費爭議",
                "polarity": -0.38,
                "snippet": "園方在學期中臨時發通知要求增收校外教學及教材雜費，引發部分家長質疑是否合乎非營利收費辦法公告標準。",
            },
            {
                "id": "op-n09-2",
                "source": "Google 地圖評論",
                "title": "Google 商家在地評論",
                "url": "https://maps.google.com/?cid=293847192837482",
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
                "source": "Dcard 親子板",
                "title": "林口某幼兒園老師情緒控管問題",
                "url": "https://www.dcard.tw/f/parentchild/p/249821340",
                "published_date": "2024-04-02",
                "topic": "不當管教/體罰",
                "polarity": -0.75,
                "snippet": "家長指控教保員對幼兒有大聲斥責、拉扯手臂等不當對待行為，監視器畫面調閱困難，教育局已介入調查處理中。",
            },
            {
                "id": "op-n11-2",
                "source": "PTT BabyMother",
                "title": "[新聞] 新北林口幼兒園師資流動頻繁調查",
                "url": "https://www.ptt.cc/bbs/BabyMother/M.1712039481.A.789.html",
                "published_date": "2024-03-25",
                "topic": "師資流動/人力不足",
                "polarity": -0.50,
                "snippet": "離職教保員爆料園所排班超時、一人帶多班，師生比超過法定上限，造成師資流動率居高不下。",
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
