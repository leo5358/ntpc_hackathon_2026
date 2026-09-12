import {
  HealthResponse,
  InstitutionListItem,
  InstitutionDetail,
  RankingsResponse,
  AccountStatementResponse,
  OpinionResponse,
  WhatIfRequest,
  WhatIfResponse,
} from "../types/api";

const BASE_URL = "/api";

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
};
