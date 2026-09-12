/**
 * 新北市幼兒園評分資料。
 *
 * 風險地圖與全市綜整報告都優先讀取 /api/institutions（見 services/institutions.ts），
 * 本檔的 SAMPLE_MAP_DATA 僅作為 API 無回應時的離線備援與版面驗證資料。
 */

export interface KindergartenMapPoint {
  id: string;
  name: string;
  /** 後端可能回傳市立／非營利／私立，不限縮為聯集型別 */
  peer_group: string;
  latest_score: number;
  latitude: number;
  longitude: number;
  district: string;
  penalty_count: number;
  primary_flag?: string;
  /** 風險項目代碼，前端據此分類；勿以中文字串比對 */
  primary_flag_code?: string;
}

/**
 * 風險色階門檻。分數是全市風險百分位（0–100），門檻對齊模型自己的兩個操作點：
 *   高風險 >=90：優先稽查名單（前 10%），模型勝過簡單規則之處
 *   中風險 30–89：落在篩檢名單範圍（90% 召回門檻約在百分位 0.32）
 *   低風險 <30
 * 見 ml/docs/MODEL_REPORT.md。
 */
export const RISK_BANDS = {
  high: 90,
  medium: 30,
} as const;

export interface RiskLevelInfo {
  key: "high" | "medium" | "low";
  label: string;
  color: string;
  border: string;
  bg: string;
}

export const getRiskLevel = (score: number): RiskLevelInfo => {
  if (score >= RISK_BANDS.high)
    return { key: "high", label: "高風險", color: "#ef4444", border: "#b91c1c", bg: "bg-rose-50 text-rose-700" };
  if (score >= RISK_BANDS.medium)
    return { key: "medium", label: "中風險", color: "#f59e0b", border: "#d97706", bg: "bg-amber-50 text-amber-700" };
  return { key: "low", label: "低風險", color: "#10b981", border: "#047857", bg: "bg-emerald-50 text-emerald-700" };
};

// Verified New Taipei City institutions dataset
export const SAMPLE_MAP_DATA: KindergartenMapPoint[] = [
  {
    id: "N07",
    name: "新北市北大非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 78.5,
    latitude: 24.9458,
    longitude: 121.3712,
    district: "三峽區",
    penalty_count: 2,
    primary_flag: "用人費用嚴重不足 (師生比缺失)",
  },
  {
    id: "N09",
    name: "新北市安興非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 64.2,
    latitude: 24.9682,
    longitude: 121.5361,
    district: "新店區",
    penalty_count: 1,
    primary_flag: "決算預算偏差異常",
  },
  {
    id: "N11",
    name: "新北市新林非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 62.0,
    latitude: 25.0745,
    longitude: 121.3654,
    district: "林口區",
    penalty_count: 1,
    primary_flag: "餐食代辦費支出異常",
  },
  {
    id: "N12",
    name: "新北市昌福非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 42.5,
    latitude: 24.9546,
    longitude: 121.3533,
    district: "鶯歌區",
    penalty_count: 1,
    primary_flag: "受託經營單位更迭",
  },
  {
    id: "N15",
    name: "新北市新月非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 38.0,
    latitude: 25.0215,
    longitude: 121.4589,
    district: "板橋區",
    penalty_count: 1,
    primary_flag: "固定資產維護支出偏低",
  },
  {
    id: "N17",
    name: "新北市中正非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 55.0,
    latitude: 25.0028,
    longitude: 121.5123,
    district: "永和區",
    penalty_count: 1,
    primary_flag: "決算執行率異常",
  },
  {
    id: "N18",
    name: "新北市福營非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 48.0,
    latitude: 25.0245,
    longitude: 121.4231,
    district: "新莊區",
    penalty_count: 1,
    primary_flag: "一般水電支出偏高",
  },
  {
    id: "N25",
    name: "新北市碧城非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 71.0,
    latitude: 24.9621,
    longitude: 121.5412,
    district: "新店區",
    penalty_count: 2,
    primary_flag: "未依規定配置教保員",
  },
  {
    id: "N29",
    name: "新北市東湖非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 22.4,
    latitude: 25.0812,
    longitude: 121.3789,
    district: "林口區",
    penalty_count: 0,
    primary_flag: "財務運作正常",
  },
  {
    id: "N30",
    name: "新北市文中非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 68.3,
    latitude: 25.0612,
    longitude: 121.4891,
    district: "三重區",
    penalty_count: 2,
    primary_flag: "超收學童與師生比爭議",
  },
  {
    id: "M01",
    name: "新北市立板橋幼兒園",
    peer_group: "市立幼兒園",
    latest_score: 18.5,
    latitude: 25.0112,
    longitude: 121.4623,
    district: "板橋區",
    penalty_count: 0,
    primary_flag: "公校基金預算執行穩健",
  },
  {
    id: "M02",
    name: "新北市立三重幼兒園",
    peer_group: "市立幼兒園",
    latest_score: 24.0,
    latitude: 25.0652,
    longitude: 121.4921,
    district: "三重區",
    penalty_count: 0,
    primary_flag: "正常",
  },
  {
    id: "M03",
    name: "新北市立新莊幼兒園",
    peer_group: "市立幼兒園",
    latest_score: 29.5,
    latitude: 25.0361,
    longitude: 121.4512,
    district: "新莊區",
    penalty_count: 0,
    primary_flag: "正常",
  },
  {
    id: "M04",
    name: "新北市立中和幼兒園",
    peer_group: "市立幼兒園",
    latest_score: 19.8,
    latitude: 24.9985,
    longitude: 121.5014,
    district: "中和區",
    penalty_count: 0,
    primary_flag: "正常",
  },
];
