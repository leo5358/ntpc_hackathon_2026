export interface HealthResponse {
  status: string;
  freshness: string;
  parser_verified_rate: number;
  opinion_coverage: number;
  version: string;
}

export interface InstitutionListItem {
  id: string;
  name: string;
  peer_group: "市立幼兒園" | "非營利園" | string;
  latest_score?: number;
  penalty_count: number;
  risk_level?: "low" | "medium" | "high";
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
