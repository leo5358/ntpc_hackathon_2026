export interface HealthResponse {
  status: string;
  freshness: string;
  /** null 代表尚未量測，報告須標示為「未量測」而非填入數字 */
  parser_verified_rate: number | null;
  parser_verified_scope: string | null;
  opinion_coverage: number | null;
  version: string;
}

export interface InstitutionListItem {
  id: string;
  name: string;
  peer_group: "市立幼兒園" | "非營利園" | string;
  latest_score?: number;
  penalty_count: number;
  risk_level?: "low" | "medium" | "high";
  latitude?: number;
  longitude?: number;
  address?: string;
}

export interface ShapContribution {
  feature: string;
  label_zh: string;
  contribution: number;
  value: any;
}

export interface PenaltyRecord {
  date: string;
  doc_no: string;
  law: string;
  violation: string;
  fine: string;
  fine_ntd: number;
  academic_year: number;
}

export interface RuleFlag {
  code: string;
  title: string;
  description: string;
  weight: number;
  source_ref?: string;
}

export interface ScoreHistoryPoint {
  academic_year: number;
  score: number;
  p_penalty: number;
  residual_z: number;
  iso_score: number;
  opinion_risk: number;
}

export interface InstitutionDetail {
  id: string;
  name: string;
  peer_group: string;
  operator?: string;
  latest_score: number;
  history: ScoreHistoryPoint[];
  shap_breakdown: ShapContribution[];
  flags: RuleFlag[];
  penalties: PenaltyRecord[];
  opinion_doc_count: number;
  source_urls: string[];
}

export interface RankingItem {
  rank: number;
  id: string;
  name: string;
  peer_group: string;
  academic_year: number;
  score: number;
  p_penalty: number;
  flag_count: number;
  has_opinion: boolean;
}

export interface RankingsResponse {
  year: number;
  group?: string;
  total: number;
  items: RankingItem[];
}

export interface AccountItem {
  account_code: string;
  account_name: string;
  category: string;
  budget: number;
  actual: number;
  variance: number;
  variance_pct?: number;
  source_page: number;
  verified: boolean;
}

export interface AccountStatementResponse {
  inst_id: string;
  inst_name: string;
  fiscal_year: number;
  items: AccountItem[];
}

export interface OpinionDocument {
  id: string;
  source: string;
  title?: string;
  url?: string;
  published_date?: string;
  topic: string;
  polarity: number;
  snippet: string;
}

export interface OpinionResponse {
  inst_id: string;
  inst_name: string;
  opinion_risk: number;
  coverage: number;
  has_opinion: boolean;
  topic_distribution: Record<string, number>;
  documents: OpinionDocument[];
}

export interface WhatIfWeights {
  penalty: number;
  residual: number;
  isolation_forest: number;
  opinion: number;
  flags: number;
}

export interface WhatIfRequest {
  weights: WhatIfWeights;
  academic_year?: number;
  peer_group?: string;
}

export interface RescoredItem {
  id: string;
  name: string;
  original_score: number;
  new_score: number;
  rank_change: number;
}

export interface WhatIfResponse {
  academic_year: number;
  weights_applied: WhatIfWeights;
  items: RescoredItem[];
}

/* ---------------------------------------------------------
 * 風險評估及處理彙總表
 * 對應「教育部風險管理推動作業原則」附件2、附件3、附件4、附件7
 * ------------------------------------------------------- */

/** 附件2：風險可能性評量標準表 */
export interface LikelihoodScaleItem {
  level: 1 | 2 | 3;
  label: string;
  description: string;
}

/** 附件2：風險影響程度評量標準表 */
export interface ImpactScaleItem {
  level: 1 | 2 | 3;
  label: string;
  image: string;
  personnel: string;
  protest: string;
  property_loss: string;
  government_operation: string;
}

/** 附件7 之「風險等級 + 風險值」欄組，判斷基準依附件3 */
export interface RiskGrade {
  likelihood: number;
  likelihood_label: string;
  impact: number;
  impact_label: string;
  risk_value: number;
  risk_level: "低度風險" | "中度風險" | "高度風險" | "極度風險" | string;
  color: string;
  tolerable: boolean;
  response: string;
}

export interface ReportEvidence {
  kind: "shap" | "penalty" | "flag" | "opinion" | "account" | string;
  label: string;
  detail: string;
  value?: any;
  source_ref?: string;
}

/** 附件7「風險評估及處理彙總表」之一列 */
export interface RiskAssessmentRow {
  seq: number;
  policy_goal: string;
  key_project: string;
  risk_item: string;
  risk_scenario: string;
  existing_control: string;
  existing: RiskGrade;
  additional_control: string;
  residual: RiskGrade;
  owner_unit: string;
  evidence: ReportEvidence[];
}

/** 附件4 現有(殘餘)風險圖像格位 */
export interface RiskMatrixCell {
  likelihood: number;
  impact: number;
  risk_value: number;
  risk_level: string;
  color: string;
  tolerable: boolean;
  response: string;
  row_seqs: number[];
}

export interface RiskReportMeta {
  agency: string;
  title: string;
  roc_year: number;
  academic_year: number;
  inst_id: string;
  inst_name: string;
  peer_group: string;
  operator?: string;
  district?: string;
  composite_score?: number;
  generated_at: string;
  model_version: string;
  data_freshness?: string;
  weights: Record<string, number>;
  is_sample: boolean;
}

export interface RiskReportSummary {
  total_items: number;
  intolerable_count: number;
  level_distribution: Record<string, number>;
  max_risk_value: number;
  residual_intolerable_count: number;
}

export interface RiskAssessmentReport {
  meta: RiskReportMeta;
  rows: RiskAssessmentRow[];
  existing_matrix: RiskMatrixCell[];
  residual_matrix: RiskMatrixCell[];
  likelihood_scale: LikelihoodScaleItem[];
  impact_scale: ImpactScaleItem[];
  tolerance_threshold: number;
  summary: RiskReportSummary;
  disclaimer: string;
  source_urls: string[];
}

export interface RiskScalesResponse {
  likelihood_scale: LikelihoodScaleItem[];
  impact_scale: ImpactScaleItem[];
  tolerance_threshold: number;
  matrix: RiskMatrixCell[];
}

/* 全市綜整報告：敘述文字生成 */

export interface NarrativePeerGroupStat {
  peer_group: string;
  count: number;
  average_score: number;
  max_score: number;
  penalty_count: number;
}

export interface NarrativeDistrictStat {
  district: string;
  count: number;
  average_score: number;
  max_score: number;
}

export interface SchoolGradeInput {
  inst_id: string;
  primary_flag?: string;
  composite_score: number;
  penalty_count: number;
}

export interface SchoolGradesRequest {
  schools: SchoolGradeInput[];
}

export interface SchoolGradeItem {
  inst_id: string;
  risk_item: string;
  grade: RiskGrade;
}

export interface SchoolGradesResponse {
  grades: SchoolGradeItem[];
}

export interface CityNarrativeRequest {
  roc_year?: number;
  academic_year?: number;
  total_institutions: number;
  average_score: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  total_penalties: number;
  peer_groups: NarrativePeerGroupStat[];
  top_districts: NarrativeDistrictStat[];
  top_flags?: string[];
  high_risk_institutions?: string[];
  opinion_coverage?: number;
  parser_verified_rate?: number;
  use_bedrock?: boolean;
}

export interface CityNarrativeResponse {
  executive_summary: string;
  key_findings: string[];
  recommendations: string[];
  /** bedrock 或 template，供前端標示文字來源 */
  generated_by: "bedrock" | "template" | string;
  model_id?: string | null;
}

/** 管線／模型輸出餵入報表產生器的單一風險訊號 */
export interface ModelSignalInput {
  code?: string;
  /** 旗標文字；未給 code 時由後端對映為風險項目代碼 */
  primary_flag?: string;
  /** 0–100 綜合風險分數；給定時優先用於換算可能性(L) */
  composite_score?: number;
  p_penalty?: number;
  severity?: number;
  penalty_count?: number;
  detail?: string;
  evidence?: ReportEvidence[];
}

export interface RiskReportBuildRequest {
  inst_id: string;
  inst_name: string;
  peer_group?: string;
  operator?: string;
  district?: string;
  academic_year?: number;
  roc_year?: number;
  composite_score?: number;
  signals: ModelSignalInput[];
  source_urls?: string[];
}
