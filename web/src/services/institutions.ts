/**
 * /api/institutions -> KindergartenMapPoint 的單一轉換點。
 *
 * 風險地圖與全市綜整報告共用本模組，避免兩頁各自轉一次而長出不一致的欄位
 * （行政區、代表旗標先前就是各自補值，導致同一份資料在兩頁不一樣）。
 */
import { api } from "./api";
import { KindergartenMapPoint, SAMPLE_MAP_DATA } from "../data/institutions";
import type { InstitutionListItem } from "../types/api";

export const toMapPoint = (item: InstitutionListItem): KindergartenMapPoint => ({
  id: item.id,
  name: item.name,
  peer_group: item.peer_group,
  latest_score: item.latest_score ?? 0,
  latitude: item.latitude ?? 25.012,
  longitude: item.longitude ?? 121.465,
  district: item.district || "未標示",
  penalty_count: item.penalty_count ?? 0,
  primary_flag: item.primary_flag ?? undefined,
  primary_flag_code: item.primary_flag_code ?? undefined,
});

export interface InstitutionsLoad {
  schools: KindergartenMapPoint[];
  /** true 表示 API 無回應，畫面用的是離線備援資料，報告須據此標示 */
  isFallback: boolean;
}

/** 取得全市機構；API 失敗時回退到離線備援資料並標記來源 */
export const loadInstitutions = async (): Promise<InstitutionsLoad> => {
  try {
    const data = await api.getInstitutions();
    if (data && data.length > 0) {
      return { schools: data.map(toMapPoint), isFallback: false };
    }
  } catch (err) {
    console.warn("Failed to fetch institutions, falling back to offline sample", err);
  }
  return { schools: SAMPLE_MAP_DATA, isFallback: true };
};
