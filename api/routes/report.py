"""Report route: 教育部風險管理推動作業原則 附件7「風險評估及處理彙總表」。"""
import logging
from typing import Optional

from fastapi import APIRouter, Query

from api import risk_matrix
from api.schemas import (
    CityNarrativeRequest,
    CityNarrativeResponse,
    ImpactScaleItem,
    LikelihoodScaleItem,
    RiskAssessmentReport,
    RiskMatrixCell,
    RiskReportBatchRequest,
    RiskReportBatchResponse,
    RiskReportBuildRequest,
    RiskScalesResponse,
    SchoolGradeItem,
    SchoolGradesRequest,
    SchoolGradesResponse,
)
from api.services import narrative, report_builder, institution_store
from api.routes.opinion import SAMPLE_ROSTER, pipeline

logger = logging.getLogger("api.routes.report")
router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/scales", response_model=RiskScalesResponse)
async def get_risk_scales():
    """附件2 評量標準表、附件3 風險容忍度與附件4 空白風險圖像。"""
    return RiskScalesResponse(
        likelihood_scale=[LikelihoodScaleItem(**item) for item in risk_matrix.LIKELIHOOD_SCALE],
        impact_scale=[ImpactScaleItem(**item) for item in risk_matrix.IMPACT_SCALE],
        tolerance_threshold=risk_matrix.RISK_TOLERANCE_THRESHOLD,
        matrix=[RiskMatrixCell(**cell) for cell in risk_matrix.build_matrix()],
    )


@router.post("/city/narrative", response_model=CityNarrativeResponse)
async def generate_city_narrative(req: CityNarrativeRequest):
    """全市綜整報告的執行摘要、關鍵發現與稽查建議。

    統計數字由前端算好傳入；Bedrock 不可用或回傳異常時自動退回規則模板，
    回應中的 generated_by 供前端標示文字來源。
    """
    stats = req.model_dump(exclude={"use_bedrock"})
    result = narrative.generate_city_narrative(stats, use_bedrock=req.use_bedrock)
    return CityNarrativeResponse(**result)


@router.post("/grades", response_model=SchoolGradesResponse)
async def grade_schools(req: SchoolGradesRequest):
    """換算多所機構的風險等級，供全市綜整報告的附件4 風險圖像標示落點。

    與 /api/report/build 共用同一段換算，避免全市圖像與機構專案報告
    對同一間園給出不同的風險值。
    """
    return SchoolGradesResponse(
        grades=[
            SchoolGradeItem(
                inst_id=school.inst_id,
                **report_builder.grade_for_school(
                    code=school.code,
                    primary_flag=school.primary_flag,
                    composite_score=school.composite_score,
                    penalty_count=school.penalty_count,
                ),
            )
            for school in req.schools
        ]
    )


@router.post("/build", response_model=RiskAssessmentReport)
async def build_report_from_model(req: RiskReportBuildRequest):
    """由管線／模型輸出直接產製報表，供批次產生或離線驗證使用。"""
    return report_builder.build_report(req)


@router.post("/build-batch", response_model=RiskReportBatchResponse)
async def build_reports_batch(req: RiskReportBatchRequest):
    """一次產製多份彙總表。

    全市綜整報告的柒章需要多所機構的附件七列，逐所發請求在全市 1,200 園的
    規模下會產生上百個往返；改由此端點一次取回。
    """
    return RiskReportBatchResponse(
        reports=[report_builder.build_report(r) for r in req.reports]
    )


@router.get("/{inst_id}", response_model=RiskAssessmentReport)
async def get_institution_report(
    inst_id: str,
    academic_year: int = Query(112, description="學年度，如 110、111、112"),
    roc_year: Optional[int] = Query(None, description="報表表頭年度，未給則以學年度+1 推算"),
    crawl: bool = Query(False, description="是否觸發即時輿情爬取與 Bedrock 分析"),
    demo: bool = Query(False, description="回傳示範資料以驗證前端版面（meta.is_sample=true）"),
):
    """產出單一機構的風險評估及處理彙總表。

    資料來源依序為：機構評分明細（旗標、裁罰、SHAP）與輿情分類結果；
    兩者皆為空時回傳無資料之空表，除非指定 demo=true。
    """
    inst_store_detail = institution_store.get_institution_detail(inst_id)
    if inst_store_detail:
        name = inst_store_detail["name"]
        district = inst_store_detail.get("district")
        peer_group = inst_store_detail.get("peer_group", "非營利園")
    else:
        inst_info = SAMPLE_ROSTER.get(inst_id, {"name": f"幼兒園-{inst_id}", "district": ""})
        name = inst_info["name"]
        district = inst_info.get("district") or None
        peer_group = "非營利園"

    signals = []
    source_urls = []

    if demo:
        signals = report_builder.sample_signals()
    else:
        opinion_payload = None
        if crawl:
            try:
                opinion_payload = pipeline.run_for_institution(
                    inst_id=inst_id, inst_name=name, district=district
                )
            except Exception as e:  # pragma: no cover - 外部服務錯誤不應中斷報表
                logger.error("Opinion pipeline failed while building report for %s: %s", inst_id, e)

        if opinion_payload:
            signals.extend(report_builder.signals_from_opinion(opinion_payload))
            source_urls = [
                doc.get("url")
                for doc in (opinion_payload.get("documents") or [])
                if doc.get("url")
            ]

        if inst_store_detail:
            signals.extend(report_builder.signals_from_detail(inst_store_detail))

    request = RiskReportBuildRequest(
        inst_id=inst_id,
        inst_name=name,
        peer_group=peer_group,
        district=district,
        academic_year=academic_year,
        roc_year=roc_year,
        signals=signals,
        source_urls=source_urls,
    )
    return report_builder.build_report(request, is_sample=demo)

