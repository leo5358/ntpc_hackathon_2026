import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Printer,
  Download,
  FileSpreadsheet,
  RefreshCw,
  Sparkles,
  AlertTriangle,
  Info,
} from "lucide-react";

import { api } from "../services/api";
import { SAMPLE_MAP_DATA, getRiskLevel, KindergartenMapPoint } from "../data/institutions";
import { computeCityStats, CityStats, HighRiskProfile } from "../services/cityReport";
import type {
  CityNarrativeResponse,
  HealthResponse,
  RiskAssessmentRow,
} from "../types/api";

const ACADEMIC_YEARS = [112, 111, 110];

/** 單一色相供量值比較使用（與品牌藍一致）；狀態色僅用於風險等級，且一律併同文字標籤 */
const SERIES_HUE = "#2563eb";

const INK = {
  primary: "text-slate-900",
  secondary: "text-slate-600",
  muted: "text-slate-500",
};

const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

/** 未量測的指標一律顯示「未量測」，不以 0% 或占位數字充數 */
const pctOrUnmeasured = (n: number | null | undefined) => (n == null ? "未量測" : pct(n));

/**
 * 模型驗證數字的單一事實來源：ml/docs/MODEL_REPORT.md（由 `python -m pipeline.s6_validate` 產生，
 * 對應 ml/models/validation_all.json）。此處若要改動，必須先重跑驗證並同步該報告。
 */
const MODEL_VALIDATION = {
  crossValidationAuc: "0.688",
  crossValidationCi: "95% CI 0.666–0.707",
  forwardAuc: "0.640",
  forwardWindow: "2018–2022 訓練 → 2023–2024 測試",
  priorityPrecision: "19.7%",
  priorityShare: "每年前 10%，約為隨機的 2.2 倍",
} as const;

/* ---------------------------------------------------------
 * 圖表元件：不引入圖表套件，純 div 量值條，列印不破版
 * ------------------------------------------------------- */

interface BarDatum {
  label: string;
  value: number;
  /** 顯示於數值位置的文字，預設為 value */
  display?: string;
  color?: string;
  note?: string;
}

const BarList: React.FC<{ data: BarDatum[]; max?: number; unit?: string }> = ({ data, max, unit }) => {
  const ceiling = max ?? Math.max(...data.map((d) => d.value), 1);
  return (
    <div className="space-y-2">
      {data.map((d) => (
        <div key={d.label} className="flex items-center gap-3" title={`${d.label}：${d.display ?? d.value}${unit ?? ""}`}>
          <div className={`w-32 shrink-0 text-xs ${INK.secondary} text-right`}>{d.label}</div>
          <div className="flex-1 h-2.5 bg-slate-100 rounded-sm overflow-hidden">
            <div
              className="h-full rounded-r"
              style={{
                width: `${ceiling ? Math.max((d.value / ceiling) * 100, d.value > 0 ? 2 : 0) : 0}%`,
                backgroundColor: d.color ?? SERIES_HUE,
              }}
            />
          </div>
          <div className={`w-24 shrink-0 text-xs font-semibold tabular-nums ${INK.primary}`}>
            {d.display ?? d.value}
            {unit ?? ""}
          </div>
          {d.note && <div className={`w-28 shrink-0 text-[11px] ${INK.muted}`}>{d.note}</div>}
        </div>
      ))}
    </div>
  );
};

const Histogram: React.FC<{ bins: { label: string; count: number }[] }> = ({ bins }) => {
  const ceiling = Math.max(...bins.map((b) => b.count), 1);
  return (
    <div>
      <div className="flex items-end gap-1.5 h-32 border-b border-slate-300">
        {bins.map((b) => (
          <div key={b.label} className="flex-1 flex flex-col items-center justify-end h-full" title={`${b.label} 分：${b.count} 所`}>
            {b.count > 0 && (
              <span className={`text-[10px] font-semibold tabular-nums ${INK.secondary} mb-0.5`}>{b.count}</span>
            )}
            <div
              className="w-full rounded-t"
              style={{
                height: `${(b.count / ceiling) * 100}%`,
                minHeight: b.count > 0 ? "4px" : "0px",
                backgroundColor: SERIES_HUE,
              }}
            />
          </div>
        ))}
      </div>
      <div className="flex gap-1.5 mt-1">
        {bins.map((b) => (
          <div key={b.label} className={`flex-1 text-center text-[9px] ${INK.muted}`}>
            {b.label}
          </div>
        ))}
      </div>
    </div>
  );
};

/** 附件4 風險圖像：以園數與園名標示落點 */
const CityRiskImage: React.FC<{ stats: CityStats }> = ({ stats }) => {
  const cellColor = (riskValue: number) => {
    if (riskValue >= 9) return "#e60000";
    if (riskValue >= 6) return "#f5a623";
    if (riskValue >= 3) return "#ccf0cc";
    return "#ffffff";
  };
  const at = (likelihood: number, impact: number) =>
    stats.matrix.find((c) => c.likelihood === likelihood && c.impact === impact);

  return (
    <div className="border border-slate-400">
      {[3, 2, 1].map((impact) => (
        <div key={impact} className="flex border-b border-slate-400 last:border-b-0">
          <div className="w-28 shrink-0 flex flex-col items-center justify-center border-r border-slate-400 bg-slate-50 py-3 text-xs font-semibold text-slate-700">
            <span>{impact === 3 ? "非常嚴重" : impact === 2 ? "嚴重" : "輕微"}</span>
            <span className="text-slate-500">（{impact}）</span>
            <span className="text-[10px] text-slate-400 mt-0.5">
              {impact === 3 ? "裁罰≥2件" : impact === 2 ? "裁罰1件" : "無裁罰"}
            </span>
          </div>
          {[1, 2, 3].map((likelihood) => {
            const cell = at(likelihood, impact);
            if (!cell) return null;
            return (
              <div
                key={likelihood}
                className="flex-1 border-r border-slate-400 last:border-r-0 p-2 min-h-[92px]"
                style={{
                  backgroundColor: cellColor(cell.risk_value),
                  color: cell.risk_value >= 9 ? "#ffffff" : "#0f172a",
                }}
              >
                <div className="text-[11px] font-semibold">
                  風險值(R)={cell.risk_value}　{cell.schools.length} 所
                </div>
                <ul className="mt-1 space-y-0.5">
                  {cell.schools.map((s) => (
                    <li key={s.id} className="text-[10px] leading-tight">
                      {s.name.replace("新北市", "")}（{s.latest_score}）
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      ))}
      <div className="flex border-t border-slate-400">
        <div className="w-28 shrink-0 border-r border-slate-400 bg-slate-50 px-2 py-2 text-[11px] leading-tight text-slate-700">
          <div>影響程度(I)</div>
          <div className="text-right">可能性(L)</div>
        </div>
        {["幾乎不可能（1）<30分", "可能（2）30–59分", "幾乎確定（3）≥60分"].map((label) => (
          <div
            key={label}
            className="flex-1 border-r border-slate-400 last:border-r-0 bg-slate-50 py-2 text-center text-[11px] font-medium text-slate-700"
          >
            {label}
          </div>
        ))}
      </div>
    </div>
  );
};

/* ---------------------------------------------------------
 * 頁面
 * ------------------------------------------------------- */

export const CityRiskReportPage: React.FC = () => {
  const [academicYear, setAcademicYear] = useState(112);
  const [useBedrock, setUseBedrock] = useState(true);
  const [narrative, setNarrative] = useState<CityNarrativeResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [attachmentRows, setAttachmentRows] = useState<Record<string, RiskAssessmentRow[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const schools: KindergartenMapPoint[] = SAMPLE_MAP_DATA;
  const stats = useMemo(() => computeCityStats(schools), [schools]);
  const rocYear = academicYear + 1;
  const generatedAt = useMemo(() => new Date().toLocaleString("zh-TW"), [narrative]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    // 資料可信度指標（失敗不阻斷報告產出）
    try {
      setHealth(await api.getHealth());
    } catch {
      setHealth(null);
    }

    try {
      const payload = {
        roc_year: rocYear,
        academic_year: academicYear,
        total_institutions: stats.total,
        average_score: stats.averageScore,
        high_risk_count: stats.levels.find((l) => l.key === "high")?.count ?? 0,
        medium_risk_count: stats.levels.find((l) => l.key === "medium")?.count ?? 0,
        low_risk_count: stats.levels.find((l) => l.key === "low")?.count ?? 0,
        total_penalties: stats.totalPenalties,
        peer_groups: stats.peerGroups.map((g) => ({
          peer_group: g.peer_group,
          count: g.count,
          average_score: g.average_score,
          max_score: g.max_score,
          penalty_count: g.penalty_count,
        })),
        top_districts: stats.districts.slice(0, 5).map((d) => ({
          district: d.district,
          count: d.count,
          average_score: d.average_score,
          max_score: d.max_score,
        })),
        top_flags: stats.flagCategories.flatMap((c) => c.flags).slice(0, 8),
        high_risk_institutions: stats.highRisk.map((h) => h.school.name),
        opinion_coverage: health?.opinion_coverage ?? undefined,
        parser_verified_rate: health?.parser_verified_rate ?? undefined,
        use_bedrock: useBedrock,
      };
      setNarrative(await api.postCityNarrative(payload));
    } catch (e) {
      setError(e instanceof Error ? e.message : "敘述文字產生失敗");
      setNarrative(null);
    }

    // 高風險園的附件7 列
    try {
      const entries = await Promise.all(
        stats.highRisk.map(async (profile) => {
          const report = await api.postRiskReport({
            inst_id: profile.school.id,
            inst_name: profile.school.name,
            peer_group: profile.school.peer_group,
            district: profile.school.district,
            academic_year: academicYear,
            roc_year: rocYear,
            composite_score: profile.school.latest_score,
            signals: [
              {
                primary_flag: profile.school.primary_flag,
                composite_score: profile.school.latest_score,
                penalty_count: profile.school.penalty_count,
                detail: `綜合風險分數 ${profile.school.latest_score} 分，歷史裁罰 ${profile.school.penalty_count} 件`,
              },
            ],
          });
          return [profile.school.id, report.rows] as const;
        })
      );
      setAttachmentRows(Object.fromEntries(entries));
    } catch {
      setAttachmentRows({});
    }

    setLoading(false);
  }, [academicYear, rocYear, stats, useBedrock, health?.opinion_coverage, health?.parser_verified_rate]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [academicYear, useBedrock]);

  const exportCsv = () => {
    const headers = ["排名", "機構代碼", "機構名稱", "同儕群組", "行政區", "風險分數", "風險等級", "裁罰件數", "主要風險旗標"];
    const rows = stats.ranked.map((s, i) => [
      String(i + 1),
      s.id,
      s.name,
      s.peer_group,
      s.district,
      String(s.latest_score),
      getRiskLevel(s.latest_score).label,
      String(s.penalty_count),
      s.primary_flag ?? "",
    ]);
    const esc = (v: string) => `"${v.replace(/"/g, '""')}"`;
    const csv = [headers, ...rows].map((r) => r.map(esc).join(",")).join("\r\n");
    const blob = new Blob([`﻿${csv}`], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `全市風險評估綜整報告_${rocYear}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const exportJson = () => {
    const blob = new Blob(
      [JSON.stringify({ meta: { rocYear, academicYear, generatedAt }, stats, narrative, health }, null, 2)],
      { type: "application/json;charset=utf-8;" }
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `city_risk_report_${rocYear}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const districtClusters = stats.districts.filter(
    (d) => d.count >= 2 && stats.highRisk.some((h) => h.school.district === d.district)
  );

  return (
    <div className="space-y-6">
      {/* 工具列 */}
      <div className="print:hidden bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center gap-4">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-slate-700">學年度:</span>
          <select
            value={academicYear}
            onChange={(e) => setAcademicYear(Number(e.target.value))}
            className="bg-slate-50 border border-slate-300 rounded-md px-3 py-1.5 text-sm focus:outline-none"
          >
            {ACADEMIC_YEARS.map((y) => (
              <option key={y} value={y}>
                {y}學年度
              </option>
            ))}
          </select>
        </div>

        <label className="flex items-center space-x-2 text-sm text-slate-700">
          <input type="checkbox" checked={useBedrock} onChange={(e) => setUseBedrock(e.target.checked)} />
          <span>以 Bedrock 生成摘要</span>
        </label>

        <div className="flex-1" />

        <button
          onClick={load}
          className="inline-flex items-center space-x-2 bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-2 rounded-lg text-sm font-medium transition"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          <span>重新產製</span>
        </button>
        <button
          onClick={exportCsv}
          className="inline-flex items-center space-x-2 bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-2 rounded-lg text-sm font-medium transition"
        >
          <FileSpreadsheet className="w-4 h-4" />
          <span>匯出 CSV</span>
        </button>
        <button
          onClick={exportJson}
          className="inline-flex items-center space-x-2 bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-2 rounded-lg text-sm font-medium transition"
        >
          <Download className="w-4 h-4" />
          <span>匯出 JSON</span>
        </button>
        <button
          onClick={() => window.print()}
          className="inline-flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition shadow-sm"
        >
          <Printer className="w-4 h-4" />
          <span>列印 / 另存 PDF</span>
        </button>
      </div>

      {error && (
        <div className="print:hidden bg-amber-50 border border-amber-200 text-amber-800 p-3 rounded-xl text-sm flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{error}（統計與表格不受影響，敘述改以規則模板呈現）</span>
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-8 print:border-0 print:shadow-none print:p-0">
        {/* 表頭 */}
        <header className="text-center space-y-1 border-b border-slate-200 pb-4">
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-wide">
            新北市政府教育局{rocYear}年幼兒園風險評估綜整報告
          </h1>
          <p className="text-sm text-slate-600">
            評估標的：{academicYear}學年度公共化幼兒園 {stats.total} 所（
            {stats.peerGroups.map((g) => `${g.peer_group} ${g.count} 所`).join("、")}）
          </p>
          <p className="text-xs text-slate-500">
            產製時間：{generatedAt}　模型版本：{health?.version ?? "0.1.0"}
            {health?.freshness && `　資料更新：${health.freshness}`}
          </p>
        </header>

        {/* 執行摘要 */}
        <section className="space-y-3 break-inside-avoid">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900">壹、執行摘要</h2>
            {narrative && (
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium ${
                  narrative.generated_by === "bedrock"
                    ? "bg-indigo-50 text-indigo-700"
                    : "bg-slate-100 text-slate-600"
                }`}
              >
                <Sparkles className="w-3 h-3" />
                {narrative.generated_by === "bedrock"
                  ? `AI 生成摘要（${narrative.model_id ?? "Bedrock"}）`
                  : "規則模板產生"}
              </span>
            )}
          </div>

          {loading && !narrative ? (
            <p className="text-sm text-slate-400">摘要產製中...</p>
          ) : (
            <>
              <p className="text-sm text-slate-700 leading-relaxed text-justify">
                {narrative?.executive_summary ?? "—"}
              </p>

              {narrative && narrative.key_findings.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {narrative.key_findings.map((finding, i) => (
                    <div key={i} className="border border-slate-200 rounded-lg p-3 bg-slate-50">
                      <div className="text-[11px] font-bold text-slate-500 mb-1">關鍵發現 {i + 1}</div>
                      <div className="text-xs text-slate-700 leading-relaxed">{finding}</div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* 關鍵指標 */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 pt-1">
            {[
              { label: "受評機構", value: `${stats.total} 所` },
              { label: "平均風險分數", value: stats.averageScore.toFixed(1) },
              { label: "高風險機構", value: `${stats.levels[0].count} 所` },
              { label: "歷史裁罰合計", value: `${stats.totalPenalties} 件` },
              { label: "有裁罰紀錄機構", value: `${stats.penalizedCount} / ${stats.total}` },
            ].map((tile) => (
              <div key={tile.label} className="border border-slate-200 rounded-lg p-3">
                <div className="text-xs text-slate-500">{tile.label}</div>
                <div className="text-xl font-extrabold text-slate-900 tabular-nums">{tile.value}</div>
              </div>
            ))}
          </div>
        </section>

        {/* 評估範圍與資料可信度 */}
        <section className="space-y-3 break-inside-avoid">
          <h2 className="text-base font-bold text-slate-900">貳、評估範圍與資料可信度</h2>
          <p className="text-xs text-slate-600 leading-relaxed">
            本報告資料來源包含地方教育發展基金決算書、全國教保資訊網裁罰與名冊鏡像資料，以及公開新聞與社群輿情。
            風險分數為 0–100 分之相對指標；最終上線模型以裁罰歷史與園所名冊屬性預測隔年受裁罰機率，
            預決算殘差與輿情訊號經實測後與隔年裁罰無顯著關聯，未納入最終評分（詳見捌章）。
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="border border-slate-200 rounded-lg p-3">
              <div className="text-xs text-slate-500">決算書解析驗算通過率</div>
              <div className="text-lg font-bold text-slate-900 tabular-nums">
                {pctOrUnmeasured(health?.parser_verified_rate)}
              </div>
              <div className="text-[11px] text-slate-500">
                {health?.parser_verified_scope ?? "尚未取得量測結果"}
              </div>
            </div>
            <div className="border border-slate-200 rounded-lg p-3">
              <div className="text-xs text-slate-500">輿情資料涵蓋率</div>
              <div className="text-lg font-bold text-amber-600 tabular-nums">
                {pctOrUnmeasured(health?.opinion_coverage)}
              </div>
              <div className="text-[11px] text-amber-700">
                {health?.opinion_coverage == null
                  ? "尚未建立全市涵蓋率量測；無輿情不等於無風險"
                  : "涵蓋率偏低，無輿情不等於無風險"}
              </div>
            </div>
            <div className="border border-slate-200 rounded-lg p-3">
              <div className="text-xs text-slate-500">資料更新時間</div>
              <div className="text-sm font-bold text-slate-900">{health?.freshness ?? "—"}</div>
              <div className="text-[11px] text-slate-500">下次更新後分數可能異動</div>
            </div>
          </div>
        </section>

        {/* 風險分布總覽 */}
        <section className="space-y-5 break-inside-avoid">
          <h2 className="text-base font-bold text-slate-900">參、風險分布總覽</h2>

          <div className="space-y-2">
            <h3 className="text-sm font-bold text-slate-800">一、風險等級分布</h3>
            <BarList
              data={stats.levels.map((l) => ({
                label: l.label,
                value: l.count,
                display: `${l.count} 所`,
                color: l.color,
                note: pct(l.ratio),
              }))}
            />
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-bold text-slate-800">二、同儕群組對比</h3>
            <div className="overflow-x-auto">
              <table className="min-w-[560px] w-full border-collapse text-xs">
                <thead className="bg-slate-100">
                  <tr>
                    <th className="border border-slate-300 px-2 py-1.5 text-left">同儕群組</th>
                    <th className="border border-slate-300 px-2 py-1.5">家數</th>
                    <th className="border border-slate-300 px-2 py-1.5">平均風險分數</th>
                    <th className="border border-slate-300 px-2 py-1.5">最高分</th>
                    <th className="border border-slate-300 px-2 py-1.5">高風險家數</th>
                    <th className="border border-slate-300 px-2 py-1.5">裁罰件數</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.peerGroups.map((g) => (
                    <tr key={g.peer_group}>
                      <td className="border border-slate-300 px-2 py-1.5 font-medium">{g.peer_group}</td>
                      <td className="border border-slate-300 px-2 py-1.5 text-center tabular-nums">{g.count}</td>
                      <td className="border border-slate-300 px-2 py-1.5 text-center tabular-nums font-bold">
                        {g.average_score.toFixed(1)}
                      </td>
                      <td className="border border-slate-300 px-2 py-1.5 text-center tabular-nums">{g.max_score}</td>
                      <td className="border border-slate-300 px-2 py-1.5 text-center tabular-nums">
                        {g.high_risk_count}
                      </td>
                      <td className="border border-slate-300 px-2 py-1.5 text-center tabular-nums">
                        {g.penalty_count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {stats.peerGroups.length >= 2 && (
              <p className="text-xs text-slate-600 leading-relaxed">
                {stats.peerGroups[0].peer_group}平均 {stats.peerGroups[0].average_score.toFixed(1)} 分，較
                {stats.peerGroups[stats.peerGroups.length - 1].peer_group}
                {stats.peerGroups[stats.peerGroups.length - 1].average_score.toFixed(1)} 分高出
                {(
                  stats.peerGroups[0].average_score -
                  stats.peerGroups[stats.peerGroups.length - 1].average_score
                ).toFixed(1)}
                分，且全部高風險機構皆集中於前者，建議查核資源優先配置於該群組。
              </p>
            )}
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-bold text-slate-800">三、行政區熱點（依平均風險分數排序前 5）</h3>
            <BarList
              data={stats.districts.slice(0, 5).map((d) => ({
                label: d.district,
                value: d.average_score,
                display: d.average_score.toFixed(1),
                note: `${d.count} 所 / 裁罰 ${d.penalty_count} 件`,
              }))}
              max={100}
              unit=" 分"
            />
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-bold text-slate-800">四、風險分數分布（每 10 分一組，單位：所）</h3>
            <Histogram bins={stats.histogram} />
            <p className="text-[11px] text-slate-500">
              中位數 {stats.medianScore.toFixed(1)} 分、最高 {stats.maxScore} 分、最低 {stats.minScore} 分。
            </p>
          </div>
        </section>

        {/* 風險圖像 */}
        <section className="space-y-3 break-inside-avoid">
          <h2 className="text-base font-bold text-slate-900">肆、全市風險圖像</h2>
          <p className="text-xs text-slate-600 leading-relaxed">
            依教育部風險管理推動作業原則附件四繪製。可能性(L) 由 0–100 風險分數換算（≥60 為 3、30–59 為 2、
            &lt;30 為 1）；影響程度(I) 由歷史裁罰件數換算（≥2 件為 3、1 件為 2、無裁罰為 1）；
            風險值 R = L × I，R ≤ 4 為可容忍風險。
          </p>
          <CityRiskImage stats={stats} />
        </section>

        {/* 風險因子拆解 */}
        <section className="space-y-3 break-inside-avoid">
          <h2 className="text-base font-bold text-slate-900">伍、風險因子拆解</h2>
          <BarList
            data={stats.flagCategories.map((c) => ({
              label: c.category,
              value: c.count,
              display: `${c.count} 所`,
              color: c.category === "無異常" ? "#94a3b8" : SERIES_HUE,
            }))}
          />
          <div className="overflow-x-auto">
            <table className="min-w-[560px] w-full border-collapse text-xs">
              <thead className="bg-slate-100">
                <tr>
                  <th className="border border-slate-300 px-2 py-1.5 text-left w-28">旗標類別</th>
                  <th className="border border-slate-300 px-2 py-1.5 text-left">具體旗標</th>
                </tr>
              </thead>
              <tbody>
                {stats.flagCategories.map((c) => (
                  <tr key={c.category}>
                    <td className="border border-slate-300 px-2 py-1.5 font-medium">{c.category}</td>
                    <td className="border border-slate-300 px-2 py-1.5 text-slate-600">
                      {c.flags.join("、") || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            {stats.penalizedCount} 所機構具歷史裁罰紀錄，合計 {stats.totalPenalties} 件；
            裁罰件數達 2 件之機構其風險分數皆在 {Math.min(
              ...stats.ranked.filter((s) => s.penalty_count >= 2).map((s) => s.latest_score)
            )} 分以上，顯示裁罰歷史與模型評分方向一致。
          </p>
        </section>

        {/* 稽查資源配置建議 */}
        <section className="space-y-3 break-inside-avoid">
          <h2 className="text-base font-bold text-slate-900">陸、稽查資源配置建議</h2>
          <ol className="space-y-2 text-sm text-slate-700 list-decimal pl-5">
            {(narrative?.recommendations ?? []).map((rec, i) => (
              <li key={i} className="leading-relaxed">
                {rec}
              </li>
            ))}
            {stats.highRisk.length > 0 && (
              <li className="leading-relaxed">
                依附件三判斷基準，風險值達 6 以上屬不可容忍風險，本年度計{" "}
                {stats.highRisk.length} 所應由管理階層督導研擬改善計畫並提供資源，查核順序建議依風險分數高低為：
                {stats.highRisk.map((h) => `${h.school.name}（${h.school.latest_score}）`).join("、")}。
              </li>
            )}
            {districtClusters.length > 0 && (
              <li className="leading-relaxed">
                {districtClusters.map((d) => `${d.district}（${d.count} 所）`).join("、")}
                同區內有多所受評機構且含高風險園，建議合併排程實地查核以節省往返人力。
              </li>
            )}
          </ol>
        </section>

        {/* 第貳部分：高風險專案報告 */}
        <section className="space-y-4 break-before-page">
          <div className="border-b border-slate-300 pb-2">
            <h2 className="text-lg font-bold text-slate-900">柒、高風險機構專案報告</h2>
            <p className="text-xs text-slate-600 mt-1">
              納入標準：綜合風險分數 ≥ 60 分，共 {stats.highRisk.length} 所。每節可獨立列印供承辦科室使用。
            </p>
          </div>

          {stats.highRisk.map((profile) => (
            <HighRiskSection
              key={profile.school.id}
              profile={profile}
              stats={stats}
              rows={attachmentRows[profile.school.id] ?? []}
            />
          ))}
        </section>

        {/* 方法論與限制 */}
        <section className="space-y-3 break-inside-avoid">
          <h2 className="text-base font-bold text-slate-900">捌、模型方法論與使用限制</h2>
          <div className="bg-slate-900 text-slate-100 p-3 rounded-lg font-mono text-[11px] overflow-x-auto">
            rank = sigmoid(intercept + Σ coef_i * z_i)　　risk_probability = sigmoid(a * logit(rank) + b)
            <span className="block text-slate-400">
              特徵：過去裁罰次數、當年是否被罰、距上次裁罰年數、核定人數、月費、立案年數、私立、非營利、延長照顧、準公共化
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              {
                label: "跨機構交叉驗證 AUC",
                value: MODEL_VALIDATION.crossValidationAuc,
                note: MODEL_VALIDATION.crossValidationCi,
              },
              {
                label: "時間外推 AUC",
                value: MODEL_VALIDATION.forwardAuc,
                note: MODEL_VALIDATION.forwardWindow,
              },
              {
                label: "優先稽查名單精準率",
                value: MODEL_VALIDATION.priorityPrecision,
                note: MODEL_VALIDATION.priorityShare,
              },
            ].map((m) => (
              <div key={m.label} className="border border-slate-200 rounded-lg p-3 text-center">
                <div className="text-[11px] text-slate-500">{m.label}</div>
                <div className="text-lg font-bold text-slate-900 tabular-nums">{m.value}</div>
                <div className="text-[10px] text-slate-500">{m.note}</div>
              </div>
            ))}
          </div>
          <p className="text-[11px] text-slate-500">
            上列數字由 <span className="font-mono">python -m pipeline.s6_validate</span> 產生，
            出處為 ml/docs/MODEL_REPORT.md；決算書解析驗算通過率見貳章。
          </p>
          <p className="text-xs text-slate-600 leading-relaxed">
            本報告輸出之風險分數為異常指標與資源優先分配輔助依據，非行政裁決或違法事實之認定；
            所有高風險預警項目均須經稽查人員比對原始財務單據與現場查核後方能定案。
            風險等級級距與處理策略引用教育部風險管理推動作業原則附件二、附件三、附件四與附件七格式。
            使用限制：上列 AUC 為全新北各類型園所之整體表現，公共化園（非營利、市立）受裁罰件數過少，
            模型在該群組內部的排序尚無可靠訊號，本報告之公共化園排序僅供查核排程參考，不應據以比較優劣。
            {narrative?.generated_by === "bedrock" &&
              "本報告執行摘要與建議由 AWS Bedrock Claude 依前述統計數字生成，內容須經承辦人員複核後方可對外引用。"}
          </p>
        </section>

        {/* 附錄 */}
        <section className="space-y-2">
          <h2 className="text-base font-bold text-slate-900">玖、附錄：全機構風險評分明細</h2>
          <div className="overflow-x-auto">
            <table className="min-w-[720px] w-full border-collapse text-xs">
              <thead className="bg-slate-100">
                <tr>
                  <th className="border border-slate-300 px-2 py-1.5 w-12">排名</th>
                  <th className="border border-slate-300 px-2 py-1.5 w-16">代碼</th>
                  <th className="border border-slate-300 px-2 py-1.5 text-left">機構名稱</th>
                  <th className="border border-slate-300 px-2 py-1.5 w-24">同儕群組</th>
                  <th className="border border-slate-300 px-2 py-1.5 w-20">行政區</th>
                  <th className="border border-slate-300 px-2 py-1.5 w-20">風險分數</th>
                  <th className="border border-slate-300 px-2 py-1.5 w-20">風險等級</th>
                  <th className="border border-slate-300 px-2 py-1.5 w-16">裁罰</th>
                  <th className="border border-slate-300 px-2 py-1.5 text-left">主要風險旗標</th>
                </tr>
              </thead>
              <tbody>
                {stats.ranked.map((s, i) => {
                  const level = getRiskLevel(s.latest_score);
                  return (
                    <tr key={s.id} className="hover:bg-slate-50">
                      <td className="border border-slate-300 px-2 py-1.5 text-center tabular-nums">{i + 1}</td>
                      <td className="border border-slate-300 px-2 py-1.5 text-center font-mono">{s.id}</td>
                      <td className="border border-slate-300 px-2 py-1.5">{s.name}</td>
                      <td className="border border-slate-300 px-2 py-1.5 text-center">{s.peer_group}</td>
                      <td className="border border-slate-300 px-2 py-1.5 text-center">{s.district}</td>
                      <td className="border border-slate-300 px-2 py-1.5 text-center tabular-nums font-bold">
                        {s.latest_score}
                      </td>
                      <td className="border border-slate-300 px-2 py-1.5 text-center">
                        <span className="inline-flex items-center gap-1">
                          <span
                            className="w-2 h-2 rounded-full inline-block"
                            style={{ backgroundColor: level.color }}
                          />
                          {level.label}
                        </span>
                      </td>
                      <td className="border border-slate-300 px-2 py-1.5 text-center tabular-nums">
                        {s.penalty_count}
                      </td>
                      <td className="border border-slate-300 px-2 py-1.5 text-slate-600">{s.primary_flag ?? "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] text-slate-500 flex items-start gap-1.5">
            <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" />
            <span>
              資料來源：本平台 {academicYear} 學年度評分結果；風險分數為模型推估之相對指標，
              數值高低不代表違法事實之有無。
            </span>
          </p>
        </section>
      </div>
    </div>
  );
};

/* ---------------------------------------------------------
 * 高風險機構專案報告區塊
 * ------------------------------------------------------- */

const HighRiskSection: React.FC<{
  profile: HighRiskProfile;
  stats: CityStats;
  rows: RiskAssessmentRow[];
}> = ({ profile, stats, rows }) => {
  const { school } = profile;
  const level = getRiskLevel(school.latest_score);

  return (
    <div className="border border-slate-300 rounded-lg p-4 space-y-3 break-inside-avoid">
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-200 pb-2">
        <div>
          <h3 className="text-sm font-bold text-slate-900">
            {profile.rank}. {school.name}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {school.peer_group}．{school.district}．代碼 {school.id}
          </p>
        </div>
        <div className="text-right">
          <span className="text-[11px] text-slate-500 block">綜合風險分數</span>
          <span className="text-2xl font-extrabold tabular-nums" style={{ color: level.color }}>
            {school.latest_score}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
        {[
          { label: "全市排名", value: `${profile.rank} / ${stats.total}` },
          { label: "百分位", value: `前 ${100 - profile.percentile}%` },
          { label: "群組內排名", value: `${profile.peer_rank} / ${profile.peer_total}` },
          { label: "高於全市平均", value: `${profile.score_gap_to_average.toFixed(1)} 分` },
        ].map((item) => (
          <div key={item.label} className="border border-slate-200 rounded p-2">
            <div className="text-[11px] text-slate-500">{item.label}</div>
            <div className="font-bold text-slate-900 tabular-nums">{item.value}</div>
          </div>
        ))}
      </div>

      <div className="text-xs text-slate-700 leading-relaxed">
        <span className="font-semibold">主要風險旗標：</span>
        {school.primary_flag ?? "—"}
        {school.penalty_count > 0 && (
          <span>；近年累計 {school.penalty_count} 件裁罰紀錄，已納入影響程度評估。</span>
        )}
      </div>

      {rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="min-w-[900px] w-full border-collapse text-[11px]">
            <thead className="bg-slate-100">
              <tr>
                <th className="border border-slate-300 px-2 py-1">風險項目</th>
                <th className="border border-slate-300 px-2 py-1">風險情境</th>
                <th className="border border-slate-300 px-2 py-1 w-12">L</th>
                <th className="border border-slate-300 px-2 py-1 w-12">I</th>
                <th className="border border-slate-300 px-2 py-1 w-20">風險值(R)</th>
                <th className="border border-slate-300 px-2 py-1">新增風險對策</th>
                <th className="border border-slate-300 px-2 py-1 w-28">主辦單位</th>
              </tr>
            </thead>
            <tbody className="align-top">
              {rows.map((row) => (
                <tr key={row.seq}>
                  <td className="border border-slate-300 px-2 py-1 font-medium">{row.risk_item}</td>
                  <td className="border border-slate-300 px-2 py-1 leading-relaxed">{row.risk_scenario}</td>
                  <td className="border border-slate-300 px-2 py-1 text-center font-bold">
                    {row.existing.likelihood}
                  </td>
                  <td className="border border-slate-300 px-2 py-1 text-center font-bold">{row.existing.impact}</td>
                  <td
                    className="border border-slate-300 px-2 py-1 text-center font-bold"
                    style={{
                      backgroundColor: row.existing.color,
                      color: row.existing.color === "#e60000" ? "#ffffff" : "#0f172a",
                    }}
                  >
                    {row.existing.risk_value}
                    <span className="block text-[10px] font-medium">{row.existing.risk_level}</span>
                  </td>
                  <td className="border border-slate-300 px-2 py-1 leading-relaxed">
                    {row.additional_control || "可容忍風險，維持自主監控"}
                  </td>
                  <td className="border border-slate-300 px-2 py-1">{row.owner_unit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="text-xs text-slate-700 leading-relaxed bg-slate-50 border border-slate-200 rounded p-2">
        <span className="font-semibold">建議查核重點：</span>
        {rows.length > 0 && rows[0].additional_control
          ? rows[0].additional_control
          : "由承辦科室依現有風險對策辦理例行訪視，並持續監控風險分數變化。"}
      </div>
    </div>
  );
};
