"""Pydantic schemas and response contracts for the API."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------
# Common & Health Models
# ---------------------------------------------------------
class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Service status")
    freshness: str = Field(default="unknown", description="Last data update timestamp")
    parser_verified_rate: Optional[float] = Field(
        default=None, description="決算書解析逐列驗算通過率；None 代表尚未量測"
    )
    parser_verified_scope: Optional[str] = Field(
        default=None, description="parser_verified_rate 的量測口徑，供報告標註來源"
    )
    opinion_coverage: Optional[float] = Field(
        default=None, description="有輿情資料之園所占比；None 代表尚未量測"
    )
    version: str = Field(default="0.1.0", description="API version")


# ---------------------------------------------------------
# Institution Models
# ---------------------------------------------------------
class InstitutionListItem(BaseModel):
    id: str = Field(..., description="Institution ID, e.g. 13111-9 or N07")
    name: str = Field(..., description="Full or normalized institution name")
    peer_group: str = Field(..., description="Peer group, e.g. 市立幼兒園 or 非營利園")
    latest_score: Optional[float] = Field(None, description="Composite risk score 0..100")
    penalty_count: int = Field(default=0, description="Total historical penalty count")
    risk_level: Optional[str] = Field(None, description="Low, Medium, High risk indicator")
    latitude: Optional[float] = Field(None, description="Latitude from preschools.json")
    longitude: Optional[float] = Field(None, description="Longitude from preschools.json")
    address: Optional[str] = Field(None, description="Institution address")
    district: Optional[str] = Field(None, description="行政區，供地圖與全市報告分組")
    primary_flag: Optional[str] = Field(None, description="權重最高之風險旗標標題")
    primary_flag_code: Optional[str] = Field(
        None, description="該旗標對應之風險項目代碼，供前端穩定分類（勿以中文字串比對）"
    )


class ShapContribution(BaseModel):
    feature: str = Field(..., description="Feature name")
    label_zh: str = Field(..., description="Plain-Chinese feature description")
    contribution: float = Field(..., description="SHAP value contribution")
    value: Any = Field(..., description="Original feature value")


class PenaltyRecord(BaseModel):
    date: str = Field(..., description="Penalty date YYYY/MM/DD")
    doc_no: str = Field(..., description="Official document number")
    law: str = Field(..., description="Violated law clause")
    violation: str = Field(..., description="Violation description")
    fine: str = Field(..., description="Fine amount text")
    fine_ntd: int = Field(..., description="Parsed fine amount in NTD")
    academic_year: int = Field(..., description="Taiwan academic year, e.g. 112")


class RuleFlag(BaseModel):
    code: str = Field(..., description="Rule flag code, e.g. BENFORD_ANOMALY")
    title: str = Field(..., description="Flag title")
    description: str = Field(..., description="Plain-Chinese explanation")
    weight: float = Field(..., description="Flag weight in risk score")
    source_ref: Optional[str] = Field(None, description="Reference page or URL")


class ScoreHistoryPoint(BaseModel):
    academic_year: int
    score: float
    p_penalty: float
    residual_z: float
    iso_score: float
    opinion_risk: float


class InstitutionDetail(BaseModel):
    id: str
    name: str
    peer_group: str
    operator: Optional[str] = None
    latest_score: float
    history: List[ScoreHistoryPoint] = []
    shap_breakdown: List[ShapContribution] = []
    flags: List[RuleFlag] = []
    penalties: List[PenaltyRecord] = []
    opinion_doc_count: int = 0
    source_urls: List[str] = []


# ---------------------------------------------------------
# Ranking Models
# ---------------------------------------------------------
class RankingItem(BaseModel):
    rank: int
    id: str
    name: str
    peer_group: str
    academic_year: int
    score: float
    p_penalty: float
    flag_count: int
    has_opinion: bool


class RankingsResponse(BaseModel):
    year: int
    group: Optional[str] = None
    total: int
    items: List[RankingItem] = []


# ---------------------------------------------------------
# Account (Budget vs Actual) Models
# ---------------------------------------------------------
class AccountItem(BaseModel):
    account_code: str
    account_name: str
    category: str
    budget: int
    actual: int
    variance: int
    variance_pct: Optional[float] = None
    source_page: int
    verified: bool


class AccountStatementResponse(BaseModel):
    inst_id: str
    inst_name: str
    fiscal_year: int
    items: List[AccountItem] = []


# ---------------------------------------------------------
# Opinion Models
# ---------------------------------------------------------
class OpinionDocument(BaseModel):
    id: str
    source: str = Field(..., description="google_places, ptt, dcard, news, etc.")
    title: Optional[str] = None
    url: Optional[str] = None
    published_date: Optional[str] = None
    topic: str = Field(..., description="L1 classification category")
    polarity: float = Field(..., description="L2 polarity -1.0 to 1.0")
    snippet: str


class OpinionResponse(BaseModel):
    inst_id: str
    inst_name: str
    opinion_risk: float
    coverage: int = Field(..., description="Number of matched documents")
    has_opinion: bool
    topic_distribution: Dict[str, int] = {}
    documents: List[OpinionDocument] = []


# ---------------------------------------------------------
# What-If Models
# ---------------------------------------------------------
class WhatIfWeights(BaseModel):
    penalty: float = Field(default=0.45, ge=0.0, le=1.0)
    residual: float = Field(default=0.20, ge=0.0, le=1.0)
    isolation_forest: float = Field(default=0.15, ge=0.0, le=1.0)
    opinion: float = Field(default=0.10, ge=0.0, le=1.0)
    flags: float = Field(default=0.10, ge=0.0, le=1.0)


class WhatIfRequest(BaseModel):
    weights: WhatIfWeights
    academic_year: Optional[int] = 112
    peer_group: Optional[str] = None


class RescoredItem(BaseModel):
    id: str
    name: str
    original_score: float
    new_score: float
    rank_change: int


class WhatIfResponse(BaseModel):
    academic_year: int
    weights_applied: WhatIfWeights
    items: List[RescoredItem] = []


# ---------------------------------------------------------
# Risk Assessment Report Models
# 對應「教育部風險管理推動作業原則」附件2、附件3、附件4、附件7
# ---------------------------------------------------------
class LikelihoodScaleItem(BaseModel):
    """附件2：風險可能性評量標準表之一列。"""

    level: int = Field(..., ge=1, le=3, description="等級(L)")
    label: str = Field(..., description="可能性，如 幾乎確定 / 可能 / 幾乎不可能")
    description: str = Field(..., description="詳細的描述")


class ImpactScaleItem(BaseModel):
    """附件2：風險影響程度評量標準表之一列。"""

    level: int = Field(..., ge=1, le=3, description="等級(I)")
    label: str = Field(..., description="影響程度，如 非常嚴重 / 嚴重 / 輕微")
    image: str = Field(..., description="形象")
    personnel: str = Field(..., description="人員")
    protest: str = Field(..., description="民眾（或部會）抗議")
    property_loss: str = Field(..., description="財物損失")
    government_operation: str = Field(..., description="影響政府運作")


class RiskGrade(BaseModel):
    """附件7 之「風險等級 + 風險值」欄組，判斷基準依附件3。"""

    likelihood: int = Field(..., ge=1, le=3, description="可能性(L)")
    likelihood_label: str = Field(..., description="可能性文字級距")
    impact: int = Field(..., ge=1, le=3, description="影響程度(I)")
    impact_label: str = Field(..., description="影響程度文字級距")
    risk_value: int = Field(..., description="風險值(R)=(L)×(I)")
    risk_level: str = Field(..., description="低度風險 / 中度風險 / 高度風險 / 極度風險")
    color: str = Field(..., description="附件4 風險圖像色階")
    tolerable: bool = Field(..., description="是否為可容忍風險（R<=4）")
    response: str = Field(..., description="附件3 對應之處理策略敘述")


class ReportEvidence(BaseModel):
    """報表列的模型佐證，確保每一格風險等級都可回溯到原始資料。"""

    kind: str = Field(..., description="shap / penalty / flag / opinion / account")
    label: str = Field(..., description="佐證標題")
    detail: str = Field(..., description="白話說明")
    value: Optional[Any] = Field(None, description="數值或原始值")
    source_ref: Optional[str] = Field(None, description="決算書頁碼、裁罰文號或來源 URL")


class RiskAssessmentRow(BaseModel):
    """附件7「風險評估及處理彙總表」之一列（11 個資料欄）。"""

    seq: int = Field(..., description="項次")
    policy_goal: str = Field(..., description="年度施政目標")
    key_project: str = Field(..., description="重要計畫項目")
    risk_item: str = Field(..., description="風險項目")
    risk_scenario: str = Field(..., description="風險情境（發生原因及影響範圍）")
    existing_control: str = Field(..., description="現有風險對策")
    existing: RiskGrade = Field(..., description="現有風險等級(L)(I)與現有風險值(R)")
    additional_control: str = Field(default="", description="新增風險對策")
    residual: RiskGrade = Field(..., description="殘餘風險等級(L)(I)與殘餘風險值(R)")
    owner_unit: str = Field(..., description="主辦單位")
    evidence: List[ReportEvidence] = Field(default_factory=list, description="模型佐證明細")


class RiskMatrixCell(BaseModel):
    """附件4 現有(殘餘)風險圖像之單一格位。"""

    likelihood: int
    impact: int
    risk_value: int
    risk_level: str
    color: str
    tolerable: bool
    response: str
    row_seqs: List[int] = Field(default_factory=list, description="落於本格之風險項目項次")


class RiskReportMeta(BaseModel):
    """報表表頭與可稽核性資訊。"""

    agency: str = Field(default="新北市政府教育局", description="機關名稱")
    title: str = Field(..., description="報表全銜，如 新北市政府教育局114年風險評估及處理彙總表")
    roc_year: int = Field(..., description="中華民國年度（表頭 ○○○年）")
    academic_year: int = Field(..., description="學年度，如 112")
    inst_id: str
    inst_name: str
    peer_group: str
    operator: Optional[str] = None
    district: Optional[str] = None
    composite_score: Optional[float] = Field(None, description="綜合風險評分 0..100")
    generated_at: str = Field(..., description="產製時間 ISO8601")
    model_version: str = Field(default="0.1.0", description="評分模型版本")
    data_freshness: Optional[str] = Field(None, description="資料更新時間")
    weights: Dict[str, float] = Field(default_factory=dict, description="綜合評分權重配置")
    is_sample: bool = Field(default=False, description="是否為示範資料（未接真實模型輸出）")


class RiskReportSummary(BaseModel):
    total_items: int = 0
    intolerable_count: int = Field(default=0, description="不可容忍風險（R>=6）項目數")
    level_distribution: Dict[str, int] = Field(default_factory=dict, description="各風險等級項目數")
    max_risk_value: int = 0
    residual_intolerable_count: int = Field(default=0, description="採行新增對策後仍不可容忍之項目數")


class RiskAssessmentReport(BaseModel):
    """完整文件報告：可直接於前端排版列印或匯出。"""

    meta: RiskReportMeta
    rows: List[RiskAssessmentRow] = []
    existing_matrix: List[RiskMatrixCell] = Field(default_factory=list, description="附件4 現有風險圖像")
    residual_matrix: List[RiskMatrixCell] = Field(default_factory=list, description="附件4 殘餘風險圖像")
    likelihood_scale: List[LikelihoodScaleItem] = []
    impact_scale: List[ImpactScaleItem] = []
    tolerance_threshold: int = Field(default=4, description="風險容忍度：風險值 4 以下予以容忍")
    summary: RiskReportSummary = Field(default_factory=RiskReportSummary)
    disclaimer: str = Field(default="", description="審計免責聲明")
    source_urls: List[str] = []


class RiskScalesResponse(BaseModel):
    """附件2 與附件3 之評量標準，供前端繪製圖例與矩陣。"""

    likelihood_scale: List[LikelihoodScaleItem] = []
    impact_scale: List[ImpactScaleItem] = []
    tolerance_threshold: int = 4
    matrix: List[RiskMatrixCell] = []


class ModelSignalInput(BaseModel):
    """管線／模型輸出餵入報表產生器的單一風險訊號。"""

    code: str = Field(default="", description="風險項目代碼，如 UNDERSTAFFING、OPINION_餐食與衛生")
    primary_flag: Optional[str] = Field(
        None, description="地圖／排行頁的旗標文字；未給 code 時由後端對映為風險項目代碼"
    )
    composite_score: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="0–100 綜合風險分數；給定時優先用於換算可能性(L)"
    )
    p_penalty: Optional[float] = Field(None, ge=0.0, le=1.0, description="XGBoost 裁罰預測機率")
    severity: Optional[float] = Field(None, ge=0.0, le=1.0, description="嚴重度 0..1（輿情或旗標）")
    penalty_count: int = Field(default=0, description="相關歷史裁罰件數")
    detail: Optional[str] = Field(None, description="補充敘述，併入風險情境")
    evidence: List[ReportEvidence] = Field(default_factory=list)


class PeerGroupStat(BaseModel):
    peer_group: str
    count: int
    average_score: float
    max_score: float
    penalty_count: int


class DistrictStat(BaseModel):
    district: str
    count: int
    average_score: float
    max_score: float


class CityNarrativeRequest(BaseModel):
    """POST /api/report/city/narrative：統計由前端算好，後端只負責敘述文字。"""

    roc_year: int = Field(default=113, description="報表年度")
    academic_year: int = Field(default=112, description="學年度")
    total_institutions: int = 0
    average_score: float = 0.0
    high_risk_count: int = Field(default=0, description="風險分數 >= 60 之機構數")
    medium_risk_count: int = 0
    low_risk_count: int = 0
    total_penalties: int = Field(default=0, description="歷史裁罰件數合計")
    peer_groups: List[PeerGroupStat] = []
    top_districts: List[DistrictStat] = []
    top_flags: List[str] = Field(default_factory=list, description="出現最多的風險旗標")
    high_risk_institutions: List[str] = Field(default_factory=list, description="高風險機構名稱")
    opinion_coverage: Optional[float] = Field(None, description="輿情資料涵蓋率 0..1")
    parser_verified_rate: Optional[float] = Field(None, description="PDF 解析驗證率 0..1")
    use_bedrock: bool = Field(default=True, description="關閉時直接使用規則模板")


class CityNarrativeResponse(BaseModel):
    executive_summary: str = ""
    key_findings: List[str] = []
    recommendations: List[str] = []
    generated_by: str = Field(default="template", description="bedrock 或 template")
    model_id: Optional[str] = None


class SchoolGradeInput(BaseModel):
    """全市風險圖像所需的單一機構輸入。"""

    inst_id: str
    code: str = Field(default="", description="風險項目代碼；優先於 primary_flag 文字對映")
    primary_flag: Optional[str] = None
    composite_score: float = Field(..., ge=0.0, le=100.0, description="0–100 綜合風險分數")
    penalty_count: int = 0


class SchoolGradesRequest(BaseModel):
    """POST /api/report/grades：一次換算多所機構的風險等級。"""

    schools: List[SchoolGradeInput] = []


class SchoolGradeItem(BaseModel):
    inst_id: str
    risk_item: str = Field(..., description="對映到的風險項目名稱")
    grade: RiskGrade = Field(..., description="現有風險等級(L)(I)與風險值(R)")


class SchoolGradesResponse(BaseModel):
    grades: List[SchoolGradeItem] = []


class RiskReportBuildRequest(BaseModel):
    """POST /api/report/build：由管線直接以模型輸出產生報表。"""

    inst_id: str
    inst_name: str
    peer_group: str = "非營利園"
    operator: Optional[str] = None
    district: Optional[str] = None
    academic_year: int = 112
    roc_year: Optional[int] = Field(None, description="未給則以學年度+1 推算")
    composite_score: Optional[float] = None
    signals: List[ModelSignalInput] = []
    source_urls: List[str] = []


class RiskReportBatchRequest(BaseModel):
    """POST /api/report/build-batch：一次產製多份彙總表，避免前端逐所發請求。"""

    reports: List[RiskReportBuildRequest] = Field(default_factory=list, max_length=200)


class RiskReportBatchResponse(BaseModel):
    reports: List[RiskAssessmentReport] = Field(default_factory=list)
