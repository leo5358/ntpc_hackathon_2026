"""Pydantic schemas and response contracts for the API."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------
# Common & Health Models
# ---------------------------------------------------------
class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Service status")
    freshness: str = Field(default="unknown", description="Last data update timestamp")
    parser_verified_rate: float = Field(default=0.0, description="PDF parse verification rate, target >0.95")
    opinion_coverage: float = Field(default=0.0, description="Proportion of schools with opinion data")
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
