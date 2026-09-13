"""將模型輸出組裝為「風險評估及處理彙總表」（教育部風險管理推動作業原則 附件7）。

流程：
    模型訊號 (ModelSignalInput)
      -> 風險項目目錄 (RISK_ITEM_CATALOG) 補齊情境、現有對策、主辦單位、影響程度基準
      -> 依附件2 級距換算 可能性(L) 與 影響程度(I)
      -> 依附件3 判斷基準算出 風險值(R) 與處理策略
      -> 依附件4 排出現有與殘餘風險圖像

所有換算門檻集中在本檔案，方便稽核人員檢視「模型分數如何變成官方級距」。
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from api import risk_matrix
from api.config import load_config
from api.schemas import (
    ImpactScaleItem,
    LikelihoodScaleItem,
    ModelSignalInput,
    ReportEvidence,
    RiskAssessmentReport,
    RiskAssessmentRow,
    RiskGrade,
    RiskMatrixCell,
    RiskReportBuildRequest,
    RiskReportMeta,
    RiskReportSummary,
)

DEFAULT_POLICY_GOAL = "提升教保服務品質，確保公共化幼兒園經費運用合規與幼兒受教安全"
DEFAULT_KEY_PROJECT = "地方教育發展基金補助公立及非營利幼兒園營運管理計畫"

DISCLAIMER = (
    "本報表由「小小守護員 (Smart Watchdog)」依公開之教育基金決算書、全國教保資訊網裁罰紀錄"
    "與公開社群輿情資料自動彙整，風險值係模型推估之相對風險指標，非違法事實之認定；"
    "風險等級級距與處理策略引用教育部風險管理推動作業原則附件2、附件3、附件4 與附件7 格式，"
    "實際稽查決策仍應由主管機關依現地查核結果認定。"
)

# ---------------------------------------------------------
# 風險項目目錄：模型代碼 -> 附件7 文字欄位與影響程度基準
# base_impact 依附件2「影響程度評量標準表」判定（人員/形象/財物損失/影響政府運作）
# ---------------------------------------------------------
RISK_ITEM_CATALOG: Dict[str, Dict[str, Any]] = {
    "UNDERSTAFFING": {
        "risk_item": "用人費用嚴重不足致教保人力配置風險",
        "risk_scenario": (
            "決算用人費用占比顯著低於同儕園所，可能反映教保員編制不足、以兼職替代專任或"
            "薪資未依規定支給，導致師生比違反教保服務人員條例，影響幼兒照顧品質。"
        ),
        "existing_control": "每學年檢核教保服務人員名冊與勞保投保紀錄，並辦理例行訪視。",
        "additional_control": (
            "將該園列入年度優先實地查核名單，要求限期提報人力配置改善計畫，"
            "並比對薪資印領清冊與決算用人費用科目。"
        ),
        "owner_unit": "新北市政府教育局幼兒教育科",
        "base_impact": 2,
    },
    "BENFORD_ANOMALY": {
        "risk_item": "決算數字分布異常（本福特定律檢定不通過）",
        "risk_scenario": (
            "決算金額首位數分布顯著偏離本福特定律預期，存在人為湊數、化整為零"
            "或分批採購規避監督之可能，影響經費使用之可信度。"
        ),
        "existing_control": "會計單位辦理決算書面審查與憑證抽查。",
        "additional_control": "調閱該年度原始憑證進行全查，並就異常科目要求說明。",
        "owner_unit": "新北市政府教育局主計室",
        "base_impact": 2,
    },
    "BUDGET_RESIDUAL": {
        "risk_item": "預決算殘差偏離同儕規模過大",
        "risk_scenario": (
            "決算數相對預算數與同儕規模之標準化偏離度過高，顯示預算編列不實、"
            "經費挪用或執行率異常，可能造成補助款未用於教保服務。"
        ),
        "existing_control": "依補助要點辦理經費核銷與結報審查。",
        "additional_control": "要求提報差異說明書，必要時暫緩撥付次期補助款。",
        "owner_unit": "新北市政府教育局主計室",
        "base_impact": 2,
    },
    "OPERATOR_CHURN": {
        "risk_item": "受託營運單位頻繁更換",
        "risk_scenario": (
            "非營利幼兒園受託法人於短期內更換，造成教保團隊不穩定、行政交接落差"
            "與課程中斷，並可能引發家長團體陳情。"
        ),
        "existing_control": "依非營利幼兒園實施辦法辦理契約履約管理與續約評選。",
        "additional_control": "強化交接查核清單，於更換後三個月內辦理專案訪視。",
        "owner_unit": "新北市政府教育局幼兒教育科",
        "base_impact": 2,
    },
    "PENALTY_RECIDIVISM": {
        "risk_item": "歷史裁罰再犯風險",
        "risk_scenario": (
            "該園近年已有教保服務相關裁罰紀錄，模型預測未來學年度再度受罰之機率偏高，"
            "顯示既有改善措施尚未落實。"
        ),
        "existing_control": "裁罰後列管追蹤改善報告，並辦理複查。",
        "additional_control": "延長列管期間並提高複查頻率，未改善者依法加重處分。",
        "owner_unit": "新北市政府教育局幼兒教育科",
        "base_impact": 2,
    },
    "OPINION_不當管教/體罰": {
        "risk_item": "幼兒不當管教或體罰事件風險",
        "risk_scenario": (
            "公開社群與新聞出現不當管教、體罰或幼兒受傷之負面討論，"
            "若屬實將造成幼兒身心傷害、家長抗議並引發全國性媒體關注。"
        ),
        "existing_control": "設置申訴信箱與監視錄影設備查核，辦理教保人員知能研習。",
        "additional_control": "立即啟動專案調查與訪談，必要時通報社政單位並暫停涉案人員職務。",
        "owner_unit": "新北市政府教育局幼兒教育科",
        "base_impact": 3,
    },
    "OPINION_餐食與衛生": {
        "risk_item": "餐食供應與環境衛生風險",
        "risk_scenario": (
            "輿情反映餐食品質不佳、食材過期或群聚腹瀉情形，"
            "可能導致食品中毒與傳染病群聚事件。"
        ),
        "existing_control": "定期辦理午餐訪視、食材抽驗與衛生稽查。",
        "additional_control": "會同衛生局辦理不預警聯合稽查，並要求公開每日菜單與食材來源。",
        "owner_unit": "新北市政府教育局幼兒教育科（會同衛生局）",
        "base_impact": 3,
    },
    "OPINION_收費爭議": {
        "risk_item": "超收費用或收退費爭議",
        "risk_scenario": (
            "家長反映巧立名目收取才藝費、代辦費或退費不合理，"
            "違反幼兒教育及照顧法收退費規定，恐引發集體陳情。"
        ),
        "existing_control": "審查收退費基準備查文件並公告於教保資訊網。",
        "additional_control": "調閱收費明細與家長繳費紀錄核對，違規者限期退還並依法裁處。",
        "owner_unit": "新北市政府教育局教保服務科",
        "base_impact": 2,
    },
    "OPINION_師資流動/人力不足": {
        "risk_item": "師資流動率過高或人力不足",
        "risk_scenario": (
            "輿情反映教師頻繁異動、代課比例偏高或未依規定配置合格教保服務人員，"
            "影響課程延續性與幼兒適應。"
        ),
        "existing_control": "查核教保服務人員異動申報與師生比。",
        "additional_control": "要求提報人力補實時程，並列入次年度續約評選指標。",
        "owner_unit": "新北市政府教育局幼兒教育科",
        "base_impact": 2,
    },
    "OPINION_設施安全": {
        "risk_item": "設施設備與公共安全風險",
        "risk_scenario": (
            "輿情反映遊具損壞、消防或逃生動線不符規定，"
            "可能造成幼兒傷害事故及公共安全檢查不合格。"
        ),
        "existing_control": "每學年辦理公共安全與消防安全檢查。",
        "additional_control": "會同工務、消防單位複查，未改善前限制使用相關場域。",
        "owner_unit": "新北市政府教育局幼兒教育科（會同消防局）",
        "base_impact": 3,
    },
    "OPINION_行政與立案": {
        "risk_item": "招生人數與立案事項違規",
        "risk_scenario": (
            "輿情或查核資料顯示超收幼兒、未報備增班或空間使用與立案內容不符，"
            "違反幼兒教育及照顧法相關規定。"
        ),
        "existing_control": "比對全國教保資訊網招生名冊與核定班級數。",
        "additional_control": "辦理現地清點並依法命其限期改善，屆期未改善者裁處。",
        "owner_unit": "新北市政府教育局教保服務科",
        "base_impact": 2,
    },
    "ASSET_MAINTENANCE_LOW": {
        "risk_item": "固定資產維護支出偏低",
        "risk_scenario": (
            "修繕維護費決算金額顯著低於同儕園所，園舍設備、遊具與消防設施可能延宕保養，"
            "累積成公共安全隱患。"
        ),
        "existing_control": "依補助要點編列修繕維護費並辦理年度設施檢查。",
        "additional_control": "要求提報園舍設備維護計畫與近三年修繕紀錄，納入公共安全檢查重點。",
        "owner_unit": "新北市政府教育局幼兒教育科",
        "base_impact": 2,
    },
    "UTILITY_COST_HIGH": {
        "risk_item": "水電等一般事務支出異常偏高",
        "risk_scenario": (
            "水電及一般事務費占比顯著高於同儕園所，可能存在計價錯誤、設備老舊耗能"
            "或費用歸屬不當之情形，排擠教保服務經費。"
        ),
        "existing_control": "會計單位辦理費用核銷與科目歸屬審查。",
        "additional_control": "調閱近三年水電費單據比對用量，確認費用歸屬與分攤基礎。",
        "owner_unit": "新北市政府教育局主計室",
        "base_impact": 1,
    },
}

# 地圖／排行頁的 primary_flag 文字 -> 風險項目目錄代碼
PRIMARY_FLAG_TO_CODE: Dict[str, str] = {
    "用人費用嚴重不足 (師生比缺失)": "UNDERSTAFFING",
    "未依規定配置教保員": "UNDERSTAFFING",
    "決算預算偏差異常": "BUDGET_RESIDUAL",
    "決算執行率異常": "BUDGET_RESIDUAL",
    "餐食代辦費支出異常": "OPINION_餐食與衛生",
    "受託經營單位更迭": "OPERATOR_CHURN",
    "超收學童與師生比爭議": "OPINION_行政與立案",
    "固定資產維護支出偏低": "ASSET_MAINTENANCE_LOW",
    "一般水電支出偏高": "UTILITY_COST_HIGH",
}


def code_from_primary_flag(flag: Optional[str]) -> str:
    """把地圖資料的 primary_flag 文字對映到風險項目代碼。

    查無對映（如「正常」「財務運作正常」）時回傳空字串，由呼叫端決定是否略過。
    """
    if not flag:
        return ""
    if flag in PRIMARY_FLAG_TO_CODE:
        return PRIMARY_FLAG_TO_CODE[flag]
    if "正常" in flag or "穩健" in flag:
        return ""
    return ""


GENERIC_ITEM: Dict[str, Any] = {
    "risk_item": "其他經模型標記之異常風險",
    "risk_scenario": "模型偵測到偏離同儕之異常訊號，尚待人工確認其成因與影響範圍。",
    "existing_control": "納入例行訪視與書面審查。",
    "additional_control": "由承辦科室人工複核模型訊號，確認是否需列入實地查核。",
    "owner_unit": "新北市政府教育局幼兒教育科",
    "base_impact": 1,
}


# ---------------------------------------------------------
# 模型分數 -> 附件2 級距的換算門檻
# ---------------------------------------------------------
def likelihood_from_score(
    p_penalty: Optional[float] = None,
    severity: Optional[float] = None,
    penalty_count: int = 0,
) -> int:
    """由模型機率與嚴重度換算可能性(L)。

    門檻（對照附件2「1年內」之時間基準）：
        >= 0.50 或 近年已有 2 件以上裁罰 -> 3 幾乎確定
        >= 0.20                          -> 2 可能
        其餘                              -> 1 幾乎不可能
    """
    signal = max(p_penalty or 0.0, severity or 0.0)
    if signal >= 0.50 or penalty_count >= 2:
        return 3
    if signal >= 0.20 or penalty_count >= 1:
        return 2
    return 1


def likelihood_from_composite_score(score: float) -> int:
    """由 0–100 綜合風險分數換算可能性(L)，門檻與前端風險色階三段一致。

        >= 60 高風險 -> 3 幾乎確定
        30 ~ 59 中風險 -> 2 可能
        < 30 低風險   -> 1 幾乎不可能
    """
    if score >= 60:
        return 3
    if score >= 30:
        return 2
    return 1


def impact_from_signal(base_impact: int, severity: Optional[float] = None, penalty_count: int = 0) -> int:
    """由風險項目基準影響程度，視嚴重度與裁罰紀錄上調一級。"""
    impact = base_impact
    if (severity or 0.0) >= 0.75 or penalty_count >= 2:
        impact += 1
    return risk_matrix.clamp_level(impact)


def residual_grade(existing: Dict[str, Any], has_additional_control: bool) -> Dict[str, Any]:
    """依附件7「新增風險對策」推估殘餘風險等級。

    採保守假設：有效之新增對策僅降低發生可能性一級，影響程度不變
    （事件一旦發生之衝擊不因管控而改變）；可容忍風險則維持原級距。
    """
    if not has_additional_control or existing["risk_value"] <= risk_matrix.RISK_TOLERANCE_THRESHOLD:
        return risk_matrix.grade(existing["likelihood"], existing["impact"])
    return risk_matrix.grade(max(1, existing["likelihood"] - 1), existing["impact"])


def _catalog_for(code: str) -> Dict[str, Any]:
    return RISK_ITEM_CATALOG.get(code, GENERIC_ITEM)


def build_row(seq: int, signal: ModelSignalInput) -> RiskAssessmentRow:
    """由單一模型訊號組出附件7 的一列。"""
    code = signal.code or code_from_primary_flag(signal.primary_flag)
    catalog = _catalog_for(code)

    # 有 0–100 綜合分數時以其為準（全市報告採分數體系），否則回到機率／嚴重度門檻
    if signal.composite_score is not None:
        likelihood = likelihood_from_composite_score(signal.composite_score)
    else:
        likelihood = likelihood_from_score(signal.p_penalty, signal.severity, signal.penalty_count)
    impact = impact_from_signal(catalog["base_impact"], signal.severity, signal.penalty_count)
    existing = risk_matrix.grade(likelihood, impact)

    additional_control = catalog["additional_control"] if not existing["tolerable"] else ""
    residual = residual_grade(existing, bool(additional_control))

    scenario = catalog["risk_scenario"]
    if signal.detail:
        scenario = f"{scenario}（模型偵測：{signal.detail}）"

    return RiskAssessmentRow(
        seq=seq,
        policy_goal=DEFAULT_POLICY_GOAL,
        key_project=DEFAULT_KEY_PROJECT,
        risk_item=catalog["risk_item"],
        risk_scenario=scenario,
        existing_control=catalog["existing_control"],
        existing=RiskGrade(**existing),
        additional_control=additional_control,
        residual=RiskGrade(**residual),
        owner_unit=catalog["owner_unit"],
        evidence=list(signal.evidence),
    )


def grade_for_school(
    primary_flag: Optional[str],
    composite_score: float,
    penalty_count: int = 0,
) -> Dict[str, Any]:
    """機構層級的風險等級，供全市風險圖像(附件4)標示落點。

    直接沿用 build_row：機構的落點就是其風險項目那一列的現有風險等級，
    確保全市圖像與該機構專案報告(附件7)不會對同一間園給出不同的風險值。
    """
    row = build_row(
        1,
        ModelSignalInput(
            primary_flag=primary_flag,
            composite_score=composite_score,
            penalty_count=penalty_count,
        ),
    )
    # 旗標對映不到目錄時（如「正常」「財務運作正常」），不要沿用泛用項目的名稱充數
    risk_item = row.risk_item if code_from_primary_flag(primary_flag) else "未對映至特定風險項目"
    return {"grade": row.existing, "risk_item": risk_item}


def _matrix_from_rows(rows: List[RiskAssessmentRow], residual: bool = False) -> List[RiskMatrixCell]:
    """將各風險項目落點填入附件4 風險圖像。"""
    placements: Dict[str, List[int]] = {}
    for row in rows:
        gradelike = row.residual if residual else row.existing
        key = f"{gradelike.likelihood},{gradelike.impact}"
        placements.setdefault(key, []).append(row.seq)
    return [RiskMatrixCell(**cell) for cell in risk_matrix.build_matrix(placements)]


def _summarize(rows: List[RiskAssessmentRow]) -> RiskReportSummary:
    distribution: Dict[str, int] = {}
    for row in rows:
        distribution[row.existing.risk_level] = distribution.get(row.existing.risk_level, 0) + 1
    return RiskReportSummary(
        total_items=len(rows),
        intolerable_count=sum(1 for row in rows if not row.existing.tolerable),
        level_distribution=distribution,
        max_risk_value=max((row.existing.risk_value for row in rows), default=0),
        residual_intolerable_count=sum(1 for row in rows if not row.residual.tolerable),
    )


def build_report(
    request: RiskReportBuildRequest,
    *,
    is_sample: bool = False,
    data_freshness: Optional[str] = None,
) -> RiskAssessmentReport:
    """由模型訊號組出完整的附件7 報表（含附件2、附件3、附件4 附表）。"""
    cfg = load_config()
    weights = cfg.get("model", {}).get("weights", {})

    rows = [build_row(idx, signal) for idx, signal in enumerate(request.signals, start=1)]
    rows.sort(key=lambda r: (-r.existing.risk_value, r.seq))
    for new_seq, row in enumerate(rows, start=1):
        row.seq = new_seq

    roc_year = request.roc_year or (request.academic_year + 1)
    meta = RiskReportMeta(
        title=f"新北市政府教育局{roc_year}年幼兒園風險評估及處理彙總表",
        roc_year=roc_year,
        academic_year=request.academic_year,
        inst_id=request.inst_id,
        inst_name=request.inst_name,
        peer_group=request.peer_group,
        operator=request.operator,
        district=request.district,
        composite_score=request.composite_score,
        generated_at=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        data_freshness=data_freshness,
        weights=weights,
        is_sample=is_sample,
    )

    return RiskAssessmentReport(
        meta=meta,
        rows=rows,
        existing_matrix=_matrix_from_rows(rows, residual=False),
        residual_matrix=_matrix_from_rows(rows, residual=True),
        likelihood_scale=[LikelihoodScaleItem(**item) for item in risk_matrix.LIKELIHOOD_SCALE],
        impact_scale=[ImpactScaleItem(**item) for item in risk_matrix.IMPACT_SCALE],
        tolerance_threshold=risk_matrix.RISK_TOLERANCE_THRESHOLD,
        summary=_summarize(rows),
        disclaimer=DISCLAIMER,
        source_urls=list(request.source_urls),
    )


# ---------------------------------------------------------
# 由既有 API 資料來源組出模型訊號
# ---------------------------------------------------------
def signals_from_opinion(opinion: Dict[str, Any]) -> List[ModelSignalInput]:
    """把 /api/opinion 的輿情分類結果轉成風險訊號。"""
    signals: List[ModelSignalInput] = []
    documents = opinion.get("documents") or []
    by_topic: Dict[str, List[Dict[str, Any]]] = {}
    for doc in documents:
        topic = doc.get("topic") or "無特定風險/一般討論"
        if topic.startswith("無特定風險"):
            continue
        by_topic.setdefault(topic, []).append(doc)

    for topic, docs in by_topic.items():
        # 極性 -1..1 轉為 0..1 嚴重度，取該議題最負面的一篇
        severity = max((max(0.0, -float(doc.get("polarity", 0.0))) for doc in docs), default=0.0)
        evidence = [
            ReportEvidence(
                kind="opinion",
                label=doc.get("title") or topic,
                detail=doc.get("snippet") or "",
                value=doc.get("polarity"),
                source_ref=doc.get("url"),
            )
            for doc in docs[:5]
        ]
        signals.append(
            ModelSignalInput(
                code=f"OPINION_{topic}",
                severity=severity,
                detail=f"{len(docs)} 則相關公開討論，最負面極性 {-severity:.2f}",
                evidence=evidence,
            )
        )
    return signals


def signals_from_detail(detail: Dict[str, Any]) -> List[ModelSignalInput]:
    """把 /api/institutions/{id} 的旗標、裁罰與 SHAP 結果轉成風險訊號。"""
    signals: List[ModelSignalInput] = []
    history = detail.get("history") or []
    latest = history[-1] if history else {}
    p_penalty = latest.get("p_penalty")
    penalties = detail.get("penalties") or []

    for flag in detail.get("flags") or []:
        signals.append(
            ModelSignalInput(
                code=flag.get("code", ""),
                p_penalty=p_penalty,
                severity=flag.get("weight"),
                penalty_count=len(penalties),
                detail=flag.get("title"),
                evidence=[
                    ReportEvidence(
                        kind="flag",
                        label=flag.get("title", ""),
                        detail=flag.get("description", ""),
                        value=flag.get("weight"),
                        source_ref=flag.get("source_ref"),
                    )
                ],
            )
        )

    if penalties:
        signals.append(
            ModelSignalInput(
                code="PENALTY_RECIDIVISM",
                p_penalty=p_penalty,
                penalty_count=len(penalties),
                detail=f"近年累計 {len(penalties)} 件裁罰紀錄",
                evidence=[
                    ReportEvidence(
                        kind="penalty",
                        label=f"{item.get('date', '')} {item.get('law', '')}",
                        detail=item.get("violation", ""),
                        value=item.get("fine_ntd"),
                        source_ref=item.get("doc_no"),
                    )
                    for item in penalties[:5]
                ],
            )
        )

    return signals


def sample_signals() -> List[ModelSignalInput]:
    """示範資料：供前端版面驗證使用，回傳之報表 meta.is_sample 為 true。"""
    return [
        ModelSignalInput(
            code="UNDERSTAFFING",
            p_penalty=0.62,
            severity=0.71,
            penalty_count=1,
            detail="用人費用占比 41.2%，低於非營利園同儕中位數 58.6%",
            evidence=[
                ReportEvidence(
                    kind="shap",
                    label="用人費用占比",
                    detail="對裁罰機率之貢獻度 +0.18，為本園最主要風險來源",
                    value=0.412,
                    source_ref="112年度決算書 p.14",
                ),
            ],
        ),
        ModelSignalInput(
            code="BUDGET_RESIDUAL",
            p_penalty=0.62,
            severity=0.44,
            detail="決算相對預算殘差 z = 2.31",
            evidence=[
                ReportEvidence(
                    kind="account",
                    label="業務費決算 vs 預算",
                    detail="決算數較預算數短列 23.4%",
                    value=-0.234,
                    source_ref="112年度決算書 p.9",
                ),
            ],
        ),
        ModelSignalInput(
            code="OPINION_餐食與衛生",
            severity=0.68,
            detail="3 則相關公開討論，最負面極性 -0.68",
            evidence=[
                ReportEvidence(
                    kind="opinion",
                    label="家長反映午餐份量與食材品質",
                    detail="社群貼文提及菜色重複與份量不足",
                    value=-0.68,
                    source_ref="https://www.dcard.tw/",
                ),
            ],
        ),
        ModelSignalInput(
            code="BENFORD_ANOMALY",
            severity=0.31,
            detail="首位數分布卡方檢定 p = 0.03",
            evidence=[
                ReportEvidence(
                    kind="flag",
                    label="本福特定律異常",
                    detail="決算金額首位數 1 出現比例偏低",
                    value=0.03,
                    source_ref="112年度決算書 p.11-13",
                ),
            ],
        ),
    ]
