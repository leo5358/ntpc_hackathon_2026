import {
  HealthResponse,
  InstitutionListItem,
  InstitutionDetail,
  RankingsResponse,
  AccountStatementResponse,
  OpinionResponse,
  WhatIfRequest,
  WhatIfResponse,
  RiskAssessmentReport,
  RiskReportBuildRequest,
  RiskScalesResponse,
  CityNarrativeRequest,
  CityNarrativeResponse,
} from "../types/api";

// 本機開發走 vite proxy 的相對路徑；部署到 S3/CloudFront 時由建置期的
// VITE_API_BASE_URL 指向 Lambda Function URL（infra/deploy_web.py 會注入）
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${endpoint}`, options);
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  getHealth: (): Promise<HealthResponse> => fetchJson<HealthResponse>("/health"),

  getInstitutions: (group?: string): Promise<InstitutionListItem[]> => {
    const query = group ? `?group=${encodeURIComponent(group)}` : "";
    return fetchJson<InstitutionListItem[]>(`/institutions${query}`);
  },

  getInstitutionDetail: (id: string): Promise<InstitutionDetail> => {
    return fetchJson<InstitutionDetail>(`/institutions/${encodeURIComponent(id)}`);
  },

  getRankings: (year = 112, group?: string, minScore?: number): Promise<RankingsResponse> => {
    const params = new URLSearchParams();
    params.set("year", year.toString());
    if (group) params.set("group", group);
    if (minScore !== undefined) params.set("min", minScore.toString());
    return fetchJson<RankingsResponse>(`/rankings?${params.toString()}`);
  },

  getAccounts: (id: string, year: number): Promise<AccountStatementResponse> => {
    return fetchJson<AccountStatementResponse>(`/accounts/${encodeURIComponent(id)}/${year}`);
  },

  getOpinion: (id: string): Promise<OpinionResponse> => {
    return fetchJson<OpinionResponse>(`/opinion/${encodeURIComponent(id)}`);
  },

  postWhatIf: (data: WhatIfRequest): Promise<WhatIfResponse> => {
    return fetchJson<WhatIfResponse>("/whatif", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  },

  /** 附件2 評量標準與附件3 風險容忍度（前端圖例與矩陣底圖） */
  getRiskScales: (): Promise<RiskScalesResponse> => fetchJson<RiskScalesResponse>("/report/scales"),

  /** 附件7 風險評估及處理彙總表 */
  getRiskReport: (
    id: string,
    options?: { academicYear?: number; rocYear?: number; crawl?: boolean; demo?: boolean }
  ): Promise<RiskAssessmentReport> => {
    const params = new URLSearchParams();
    if (options?.academicYear !== undefined) params.set("academic_year", options.academicYear.toString());
    if (options?.rocYear !== undefined) params.set("roc_year", options.rocYear.toString());
    if (options?.crawl) params.set("crawl", "true");
    if (options?.demo) params.set("demo", "true");
    const query = params.toString();
    return fetchJson<RiskAssessmentReport>(
      `/report/${encodeURIComponent(id)}${query ? `?${query}` : ""}`
    );
  },

  /** 全市綜整報告的執行摘要與建議（Bedrock 生成，失敗由後端退回規則模板） */
  postCityNarrative: (data: CityNarrativeRequest): Promise<CityNarrativeResponse> => {
    return fetchJson<CityNarrativeResponse>("/report/city/narrative", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  },

  /** 由模型輸出直接產製報表（批次或離線驗證） */
  postRiskReport: (data: RiskReportBuildRequest): Promise<RiskAssessmentReport> => {
    return fetchJson<RiskAssessmentReport>("/report/build", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  },
};
