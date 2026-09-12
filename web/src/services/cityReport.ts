/**
 * 全市綜整報告的統計計算（純函式，無 I/O）。
 *
 * 所有數字都在此集中計算，頁面只負責排版；風險分級一律取用
 * data/institutions.ts 的 RISK_BANDS，避免與地圖頁分級不一致。
 */
import {
  KindergartenMapPoint,
  RISK_BANDS,
  getRiskLevel,
} from "../data/institutions";

export interface LevelBucket {
  key: "high" | "medium" | "low";
  label: string;
  color: string;
  count: number;
  ratio: number;
}

export interface PeerGroupStat {
  peer_group: string;
  count: number;
  average_score: number;
  max_score: number;
  penalty_count: number;
  high_risk_count: number;
}

export interface DistrictStat {
  district: string;
  count: number;
  average_score: number;
  max_score: number;
  penalty_count: number;
}

export interface HistogramBin {
  lower: number;
  upper: number;
  label: string;
  count: number;
}

export interface FlagCategoryStat {
  category: "人力配置" | "財務執行" | "治理與立案" | "設施與環境" | "無異常";
  count: number;
  flags: string[];
}

export interface MatrixPlacement {
  likelihood: number;
  impact: number;
  risk_value: number;
  schools: KindergartenMapPoint[];
}

export interface HighRiskProfile {
  school: KindergartenMapPoint;
  rank: number;
  percentile: number;
  peer_rank: number;
  peer_total: number;
  score_gap_to_average: number;
}

export interface CityStats {
  total: number;
  averageScore: number;
  medianScore: number;
  maxScore: number;
  minScore: number;
  totalPenalties: number;
  penalizedCount: number;
  levels: LevelBucket[];
  peerGroups: PeerGroupStat[];
  districts: DistrictStat[];
  histogram: HistogramBin[];
  flagCategories: FlagCategoryStat[];
  matrix: MatrixPlacement[];
  highRisk: HighRiskProfile[];
  ranked: KindergartenMapPoint[];
}

const round1 = (n: number) => Math.round(n * 10) / 10;

const mean = (values: number[]) =>
  values.length === 0 ? 0 : values.reduce((acc, v) => acc + v, 0) / values.length;

const median = (values: number[]) => {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
};

/** 風險旗標歸類，用於「風險因子拆解」章節 */
export const categorizeFlag = (flag?: string): FlagCategoryStat["category"] => {
  if (!flag || flag.includes("正常") || flag.includes("穩健")) return "無異常";
  if (flag.includes("用人費用") || flag.includes("教保員") || flag.includes("師生比")) return "人力配置";
  if (flag.includes("決算") || flag.includes("預算") || flag.includes("支出") || flag.includes("水電"))
    return "財務執行";
  if (flag.includes("超收") || flag.includes("受託") || flag.includes("立案")) return "治理與立案";
  return "設施與環境";
};

/** 0–100 分換算教育部可能性(L)：>=60 -> 3、30-59 -> 2、<30 -> 1（與後端 likelihood_from_composite_score 一致） */
export const likelihoodFromScore = (score: number): number => {
  if (score >= RISK_BANDS.high) return 3;
  if (score >= RISK_BANDS.medium) return 2;
  return 1;
};

/** 裁罰件數換算影響程度(I)：>=2 件 -> 3、1 件 -> 2、無 -> 1 */
export const impactFromPenalties = (penaltyCount: number): number => {
  if (penaltyCount >= 2) return 3;
  if (penaltyCount === 1) return 2;
  return 1;
};

export const computeCityStats = (schools: KindergartenMapPoint[]): CityStats => {
  const total = schools.length;
  const scores = schools.map((s) => s.latest_score);
  const averageScore = round1(mean(scores));
  const ranked = [...schools].sort((a, b) => b.latest_score - a.latest_score);

  // 風險等級分布
  const levelDefs: Array<{ key: LevelBucket["key"]; label: string; color: string }> = [
    { key: "high", label: "高風險 (≥60)", color: "#ef4444" },
    { key: "medium", label: "中風險 (30–59)", color: "#f59e0b" },
    { key: "low", label: "低風險 (<30)", color: "#10b981" },
  ];
  const levels: LevelBucket[] = levelDefs.map((def) => {
    const count = schools.filter((s) => getRiskLevel(s.latest_score).key === def.key).length;
    return { ...def, count, ratio: total ? count / total : 0 };
  });

  // 同儕群組對比
  const groupNames = Array.from(new Set(schools.map((s) => s.peer_group)));
  const peerGroups: PeerGroupStat[] = groupNames
    .map((name) => {
      const members = schools.filter((s) => s.peer_group === name);
      return {
        peer_group: name,
        count: members.length,
        average_score: round1(mean(members.map((m) => m.latest_score))),
        max_score: Math.max(...members.map((m) => m.latest_score)),
        penalty_count: members.reduce((acc, m) => acc + m.penalty_count, 0),
        high_risk_count: members.filter((m) => m.latest_score >= RISK_BANDS.high).length,
      };
    })
    .sort((a, b) => b.average_score - a.average_score);

  // 行政區熱點
  const districtNames = Array.from(new Set(schools.map((s) => s.district)));
  const districts: DistrictStat[] = districtNames
    .map((name) => {
      const members = schools.filter((s) => s.district === name);
      return {
        district: name,
        count: members.length,
        average_score: round1(mean(members.map((m) => m.latest_score))),
        max_score: Math.max(...members.map((m) => m.latest_score)),
        penalty_count: members.reduce((acc, m) => acc + m.penalty_count, 0),
      };
    })
    .sort((a, b) => b.average_score - a.average_score);

  // 分數分布直方圖（10 分一段）
  const histogram: HistogramBin[] = Array.from({ length: 10 }, (_, i) => {
    const lower = i * 10;
    const upper = lower + 10;
    const count = schools.filter(
      (s) => s.latest_score >= lower && (upper === 100 ? s.latest_score <= 100 : s.latest_score < upper)
    ).length;
    return { lower, upper, label: `${lower}–${upper === 100 ? 100 : upper - 1}`, count };
  });

  // 旗標歸類
  const categories: FlagCategoryStat["category"][] = [
    "人力配置",
    "財務執行",
    "治理與立案",
    "設施與環境",
    "無異常",
  ];
  const flagCategories: FlagCategoryStat[] = categories
    .map((category) => {
      const members = schools.filter((s) => categorizeFlag(s.primary_flag) === category);
      return {
        category,
        count: members.length,
        flags: Array.from(new Set(members.map((m) => m.primary_flag).filter(Boolean) as string[])),
      };
    })
    .filter((c) => c.count > 0);

  // 附件4 風險圖像落點
  const matrix: MatrixPlacement[] = [];
  for (const impact of [3, 2, 1]) {
    for (const likelihood of [1, 2, 3]) {
      matrix.push({
        likelihood,
        impact,
        risk_value: likelihood * impact,
        schools: schools.filter(
          (s) =>
            likelihoodFromScore(s.latest_score) === likelihood &&
            impactFromPenalties(s.penalty_count) === impact
        ),
      });
    }
  }

  // 高風險專案報告對象
  const highRisk: HighRiskProfile[] = ranked
    .filter((s) => s.latest_score >= RISK_BANDS.high)
    .map((school) => {
      const rank = ranked.findIndex((s) => s.id === school.id) + 1;
      const peers = ranked.filter((s) => s.peer_group === school.peer_group);
      return {
        school,
        rank,
        percentile: total ? Math.round(((total - rank) / total) * 100) : 0,
        peer_rank: peers.findIndex((s) => s.id === school.id) + 1,
        peer_total: peers.length,
        score_gap_to_average: round1(school.latest_score - averageScore),
      };
    });

  return {
    total,
    averageScore,
    medianScore: round1(median(scores)),
    maxScore: total ? Math.max(...scores) : 0,
    minScore: total ? Math.min(...scores) : 0,
    totalPenalties: schools.reduce((acc, s) => acc + s.penalty_count, 0),
    penalizedCount: schools.filter((s) => s.penalty_count > 0).length,
    levels,
    peerGroups,
    districts,
    histogram,
    flagCategories,
    matrix,
    highRisk,
    ranked,
  };
};
