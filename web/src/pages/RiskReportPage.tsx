import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  ArrowLeft,
  Printer,
  Download,
  RefreshCw,
  FileSpreadsheet,
  AlertTriangle,
  Info,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

import { api } from "../services/api";
import type {
  RiskAssessmentReport,
  RiskAssessmentRow,
  RiskGrade,
  RiskMatrixCell,
} from "../types/api";

const ACADEMIC_YEARS = [112, 111, 110];

/** 附件4 色階：低度風險為白底，需補邊框才看得出格線 */
const gradeStyle = (color: string): React.CSSProperties => ({
  backgroundColor: color,
  color: color === "#e60000" ? "#ffffff" : "#0f172a",
});

const RiskValueCell: React.FC<{ grade: RiskGrade }> = ({ grade }) => (
  <div
    className="rounded-md px-2 py-1 text-center border border-slate-300 leading-tight"
    style={gradeStyle(grade.color)}
    title={grade.response}
  >
    <span className="font-bold text-base">{grade.risk_value}</span>
    <span className="block text-[11px] font-medium">{grade.risk_level}</span>
  </div>
);

/** 附件4：現有(殘餘)風險圖像，版面與原表一致（影響程度由上而下 3→1，可能性由左而右 1→3） */
const RiskImage: React.FC<{ title: string; cells: RiskMatrixCell[] }> = ({ title, cells }) => {
  const at = (likelihood: number, impact: number) =>
    cells.find((c) => c.likelihood === likelihood && c.impact === impact);

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-bold text-slate-800">{title}</h3>
      <div className="border border-slate-400">
        {[3, 2, 1].map((impact) => (
          <div key={impact} className="flex border-b border-slate-400 last:border-b-0">
            <div className="w-24 shrink-0 flex flex-col items-center justify-center border-r border-slate-400 bg-slate-50 py-4 text-xs font-semibold text-slate-700">
              <span>{impact === 3 ? "非常嚴重" : impact === 2 ? "嚴重" : "輕微"}</span>
              <span className="text-slate-500">（{impact}）</span>
            </div>
            {[1, 2, 3].map((likelihood) => {
              const cell = at(likelihood, impact);
              if (!cell) return null;
              return (
                <div
                  key={likelihood}
                  className="flex-1 border-r border-slate-400 last:border-r-0 p-2 min-h-[86px]"
                  style={gradeStyle(cell.color)}
                >
                  <div className="text-[11px] font-semibold">
                    風險值(R)={cell.risk_value}（{cell.risk_level}）
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {cell.row_seqs.map((seq) => (
                      <span
                        key={seq}
                        className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-slate-900/85 text-white text-[10px] font-bold"
                        title={`風險項目 ${seq}`}
                      >
                        {seq}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
        <div className="flex border-t border-slate-400">
          <div className="w-24 shrink-0 border-r border-slate-400 bg-slate-50 px-2 py-2 text-[11px] leading-tight text-slate-700">
            <div>影響程度(I)</div>
            <div className="text-right">可能性(L)</div>
          </div>
          {["幾乎不可能（1）", "可能（2）", "幾乎確定（3）"].map((label) => (
            <div
              key={label}
              className="flex-1 border-r border-slate-400 last:border-r-0 bg-slate-50 py-2 text-center text-xs font-medium text-slate-700"
            >
              {label}
            </div>
          ))}
        </div>
      </div>
      <p className="text-[11px] text-slate-500">
        說明：依據風險管理之步驟，將各風險項目依其風險值（影響程度×可能性）填入表格中之對應位置。
      </p>
    </div>
  );
};

const CSV_HEADERS = [
  "項次",
  "年度施政目標",
  "重要計畫項目",
  "風險項目",
  "風險情境",
  "現有風險對策",
  "現有風險等級-可能性(L)",
  "現有風險等級-影響程度(I)",
  "現有風險值(R)=(L)x(I)",
  "新增風險對策",
  "殘餘風險等級-可能性(L)",
  "殘餘風險等級-影響程度(I)",
  "殘餘風險值(R)=(L)x(I)",
  "主辦單位",
];

const toCsvRow = (row: RiskAssessmentRow): string[] => [
  String(row.seq),
  row.policy_goal,
  row.key_project,
  row.risk_item,
  row.risk_scenario,
  row.existing_control,
  String(row.existing.likelihood),
  String(row.existing.impact),
  String(row.existing.risk_value),
  row.additional_control,
  String(row.residual.likelihood),
  String(row.residual.impact),
  String(row.residual.risk_value),
  row.owner_unit,
];

const escapeCsv = (value: string) => `"${(value ?? "").replace(/"/g, '""')}"`;

export const RiskReportPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const instId = id || "N07";

  const [report, setReport] = useState<RiskAssessmentReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [academicYear, setAcademicYear] = useState(112);
  // 預設走真實訊號；示範資料須由使用者主動勾選，避免每間園都印出同一份樣板
  const [demo, setDemo] = useState(false);
  const [crawl, setCrawl] = useState(false);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getRiskReport(instId, { academicYear, demo, crawl });
      setReport(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "報表載入失敗");
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, [instId, academicYear, demo, crawl]);

  useEffect(() => {
    load();
  }, [load]);

  const toggleRow = (seq: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(seq)) next.delete(seq);
      else next.add(seq);
      return next;
    });
  };

  const exportCsv = () => {
    if (!report) return;
    const lines = [
      CSV_HEADERS.map(escapeCsv).join(","),
      ...report.rows.map((row) => toCsvRow(row).map(escapeCsv).join(",")),
    ];
    // BOM 供 Excel 正確辨識 UTF-8
    const blob = new Blob([`﻿${lines.join("\r\n")}`], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `風險評估及處理彙總表_${report.meta.inst_name}_${report.meta.roc_year}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const exportJson = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `risk_report_${report.meta.inst_id}_${report.meta.roc_year}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const generatedAt = useMemo(() => {
    if (!report) return "";
    const d = new Date(report.meta.generated_at);
    return Number.isNaN(d.getTime()) ? report.meta.generated_at : d.toLocaleString("zh-TW");
  }, [report]);

  return (
    <div className="space-y-6">
      {/* 工具列（列印時隱藏） */}
      <div className="print:hidden space-y-4">
        <Link
          to={`/i/${instId}`}
          className="inline-flex items-center space-x-1.5 text-sm font-medium text-slate-500 hover:text-slate-800 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>返回機構詳情</span>
        </Link>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center gap-4">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-slate-700">機構 ID:</span>
            <input
              value={instId}
              onChange={(e) => navigate(`/report/${encodeURIComponent(e.target.value || "N07")}`)}
              className="w-28 bg-slate-50 border border-slate-300 rounded-md px-3 py-1.5 text-sm focus:outline-none"
            />
          </div>

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
            <input type="checkbox" checked={demo} onChange={(e) => setDemo(e.target.checked)} />
            <span>示範資料</span>
          </label>

          <label className="flex items-center space-x-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={crawl}
              disabled={demo}
              onChange={(e) => setCrawl(e.target.checked)}
            />
            <span className={demo ? "text-slate-400" : ""}>即時輿情分析</span>
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
            disabled={!report || report.rows.length === 0}
            className="inline-flex items-center space-x-2 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-700 px-3 py-2 rounded-lg text-sm font-medium transition"
          >
            <FileSpreadsheet className="w-4 h-4" />
            <span>匯出 CSV</span>
          </button>
          <button
            onClick={exportJson}
            disabled={!report}
            className="inline-flex items-center space-x-2 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-700 px-3 py-2 rounded-lg text-sm font-medium transition"
          >
            <Download className="w-4 h-4" />
            <span>匯出 JSON</span>
          </button>
          <button
            onClick={() => window.print()}
            disabled={!report}
            className="inline-flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition shadow-sm"
          >
            <Printer className="w-4 h-4" />
            <span>列印 / 另存 PDF</span>
          </button>
        </div>
      </div>

      {loading && (
        <div className="bg-white p-8 rounded-xl border border-slate-200 text-center text-slate-500 text-sm">
          報表產製中...
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm flex items-start space-x-2">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {report && !loading && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-8 print:border-0 print:shadow-none print:p-0">
          {/* 表頭 */}
          <header className="text-center space-y-1 border-b border-slate-200 pb-4">
            {report.meta.is_sample && (
              <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 text-xs font-semibold">
                <Info className="w-3.5 h-3.5" />
                <span>示範資料：本表為版面驗證用，非真實模型輸出</span>
              </div>
            )}
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-wide">{report.meta.title}</h1>
            <p className="text-sm text-slate-600">
              受評機構：{report.meta.inst_name}（{report.meta.peer_group}
              {report.meta.district ? `．${report.meta.district}` : ""}）
              機構代碼：{report.meta.inst_id}　{report.meta.academic_year}學年度
            </p>
            <p className="text-xs text-slate-500">
              產製時間：{generatedAt}　模型版本：{report.meta.model_version}
              {report.meta.composite_score != null && `　綜合風險評分：${report.meta.composite_score.toFixed(1)}`}
              {report.meta.data_freshness && `　資料更新：${report.meta.data_freshness}`}
            </p>
          </header>

          {/* 摘要 */}
          <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              { label: "風險項目數", value: report.summary.total_items, tone: "text-slate-900" },
              {
                label: `不可容忍風險（R>${report.tolerance_threshold}）`,
                value: report.summary.intolerable_count,
                tone: "text-red-600",
              },
              { label: "最高風險值", value: report.summary.max_risk_value, tone: "text-amber-600" },
              {
                label: "採行新增對策後仍不可容忍",
                value: report.summary.residual_intolerable_count,
                tone: "text-orange-600",
              },
            ].map((tile) => (
              <div key={tile.label} className="border border-slate-200 rounded-lg p-3 bg-slate-50">
                <div className="text-xs text-slate-500">{tile.label}</div>
                <div className={`text-2xl font-extrabold ${tile.tone}`}>{tile.value}</div>
              </div>
            ))}
          </section>

          {/* 附件7 主表 */}
          <section className="space-y-2">
            <h2 className="text-base font-bold text-slate-900">壹、風險評估及處理彙總表</h2>
            <div className="overflow-x-auto">
              <table className="min-w-[1400px] w-full border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-100 text-slate-800">
                    <th rowSpan={2} className="border border-slate-400 px-2 py-2 w-12">項次</th>
                    <th rowSpan={2} className="border border-slate-400 px-2 py-2 w-40">年度施政目標</th>
                    <th rowSpan={2} className="border border-slate-400 px-2 py-2 w-40">重要計畫項目</th>
                    <th rowSpan={2} className="border border-slate-400 px-2 py-2 w-40">風險項目</th>
                    <th rowSpan={2} className="border border-slate-400 px-2 py-2 w-72">風險情境</th>
                    <th rowSpan={2} className="border border-slate-400 px-2 py-2 w-56">現有風險對策</th>
                    <th colSpan={2} className="border border-slate-400 px-2 py-1">現有風險等級</th>
                    <th rowSpan={2} className="border border-slate-400 px-2 py-2 w-24">
                      現有風險值(R)=(L)×(I)
                    </th>
                    <th rowSpan={2} className="border border-slate-400 px-2 py-2 w-56">新增風險對策</th>
                    <th colSpan={2} className="border border-slate-400 px-2 py-1">殘餘風險等級</th>
                    <th rowSpan={2} className="border border-slate-400 px-2 py-2 w-24">
                      殘餘風險值(R)=(L)×(I)
                    </th>
                    <th rowSpan={2} className="border border-slate-400 px-2 py-2 w-32">主辦單位</th>
                  </tr>
                  <tr className="bg-slate-100 text-slate-800">
                    <th className="border border-slate-400 px-2 py-1 w-16">可能性(L)</th>
                    <th className="border border-slate-400 px-2 py-1 w-16">影響程度(I)</th>
                    <th className="border border-slate-400 px-2 py-1 w-16">可能性(L)</th>
                    <th className="border border-slate-400 px-2 py-1 w-16">影響程度(I)</th>
                  </tr>
                </thead>
                <tbody className="align-top">
                  {report.rows.length === 0 && (
                    <tr>
                      <td colSpan={14} className="border border-slate-400 px-3 py-8 text-center text-slate-500">
                        查無風險項目：模型分數尚未落地，可勾選「示範資料」檢視版面，或改以
                        POST /api/report/build 帶入管線輸出。
                      </td>
                    </tr>
                  )}
                  {report.rows.map((row) => (
                    <React.Fragment key={row.seq}>
                      <tr className="hover:bg-slate-50">
                        <td className="border border-slate-400 px-2 py-2 text-center font-semibold">
                          <button
                            onClick={() => toggleRow(row.seq)}
                            className="inline-flex items-center space-x-1 print:hidden"
                            title="展開模型佐證"
                          >
                            {expanded.has(row.seq) ? (
                              <ChevronDown className="w-3.5 h-3.5" />
                            ) : (
                              <ChevronRight className="w-3.5 h-3.5" />
                            )}
                            <span>{row.seq}</span>
                          </button>
                          <span className="hidden print:inline">{row.seq}</span>
                        </td>
                        <td className="border border-slate-400 px-2 py-2 leading-relaxed">{row.policy_goal}</td>
                        <td className="border border-slate-400 px-2 py-2 leading-relaxed">{row.key_project}</td>
                        <td className="border border-slate-400 px-2 py-2 font-medium leading-relaxed">
                          {row.risk_item}
                        </td>
                        <td className="border border-slate-400 px-2 py-2 leading-relaxed">{row.risk_scenario}</td>
                        <td className="border border-slate-400 px-2 py-2 leading-relaxed">{row.existing_control}</td>
                        <td className="border border-slate-400 px-2 py-2 text-center">
                          <div className="font-bold">{row.existing.likelihood}</div>
                          <div className="text-[10px] text-slate-500">{row.existing.likelihood_label}</div>
                        </td>
                        <td className="border border-slate-400 px-2 py-2 text-center">
                          <div className="font-bold">{row.existing.impact}</div>
                          <div className="text-[10px] text-slate-500">{row.existing.impact_label}</div>
                        </td>
                        <td className="border border-slate-400 px-1.5 py-2">
                          <RiskValueCell grade={row.existing} />
                        </td>
                        <td className="border border-slate-400 px-2 py-2 leading-relaxed">
                          {row.additional_control || (
                            <span className="text-slate-400">可容忍風險，維持自主監控</span>
                          )}
                        </td>
                        <td className="border border-slate-400 px-2 py-2 text-center">
                          <div className="font-bold">{row.residual.likelihood}</div>
                          <div className="text-[10px] text-slate-500">{row.residual.likelihood_label}</div>
                        </td>
                        <td className="border border-slate-400 px-2 py-2 text-center">
                          <div className="font-bold">{row.residual.impact}</div>
                          <div className="text-[10px] text-slate-500">{row.residual.impact_label}</div>
                        </td>
                        <td className="border border-slate-400 px-1.5 py-2">
                          <RiskValueCell grade={row.residual} />
                        </td>
                        <td className="border border-slate-400 px-2 py-2 leading-relaxed">{row.owner_unit}</td>
                      </tr>
                      {expanded.has(row.seq) && row.evidence.length > 0 && (
                        <tr className="print:hidden">
                          <td colSpan={14} className="border border-slate-400 bg-slate-50 px-4 py-3">
                            <div className="text-[11px] font-bold text-slate-700 mb-2">
                              模型佐證（可回溯至原始資料）
                            </div>
                            <ul className="space-y-1.5">
                              {row.evidence.map((ev, i) => (
                                <li key={i} className="text-[11px] text-slate-600 flex flex-wrap gap-x-2">
                                  <span className="px-1.5 py-0.5 rounded bg-slate-200 font-mono uppercase">
                                    {ev.kind}
                                  </span>
                                  <span className="font-semibold text-slate-800">{ev.label}</span>
                                  <span>{ev.detail}</span>
                                  {ev.value != null && <span className="font-mono">值：{String(ev.value)}</span>}
                                  {ev.source_ref && <span className="text-slate-500">來源：{ev.source_ref}</span>}
                                </li>
                              ))}
                            </ul>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* 附件4 風險圖像 */}
          <section className="space-y-4 break-inside-avoid">
            <h2 className="text-base font-bold text-slate-900">貳、風險圖像</h2>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <RiskImage title="現有風險圖像" cells={report.existing_matrix} />
              <RiskImage title="殘餘風險圖像" cells={report.residual_matrix} />
            </div>
          </section>

          {/* 附件2、附件3 級距 */}
          <section className="space-y-4 break-inside-avoid">
            <h2 className="text-base font-bold text-slate-900">參、評量標準與風險容忍度</h2>
            <p className="text-xs text-slate-600">
              風險值(R) = 可能性(L) × 影響程度(I)；風險容忍度為風險值 {report.tolerance_threshold}{" "}
              以下予以容忍，風險值六以上屬不可容忍風險，應研擬新增風險對策。
            </p>

            <div className="overflow-x-auto">
              <table className="min-w-[560px] w-full border-collapse text-xs">
                <caption className="text-left text-sm font-bold text-slate-800 pb-1">風險可能性評量標準表</caption>
                <thead className="bg-slate-100">
                  <tr>
                    <th className="border border-slate-400 px-2 py-1.5 w-16">等級(L)</th>
                    <th className="border border-slate-400 px-2 py-1.5 w-28">可能性</th>
                    <th className="border border-slate-400 px-2 py-1.5">詳細的描述</th>
                  </tr>
                </thead>
                <tbody>
                  {report.likelihood_scale.map((item) => (
                    <tr key={item.level}>
                      <td className="border border-slate-400 px-2 py-1.5 text-center font-bold">{item.level}</td>
                      <td className="border border-slate-400 px-2 py-1.5 text-center">{item.label}</td>
                      <td className="border border-slate-400 px-2 py-1.5">{item.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-[900px] w-full border-collapse text-xs">
                <caption className="text-left text-sm font-bold text-slate-800 pb-1">風險影響程度評量標準表</caption>
                <thead className="bg-slate-100">
                  <tr>
                    <th className="border border-slate-400 px-2 py-1.5 w-16">等級(I)</th>
                    <th className="border border-slate-400 px-2 py-1.5 w-24">影響程度</th>
                    <th className="border border-slate-400 px-2 py-1.5">形象</th>
                    <th className="border border-slate-400 px-2 py-1.5 w-16">人員</th>
                    <th className="border border-slate-400 px-2 py-1.5 w-32">民眾(或部會)抗議</th>
                    <th className="border border-slate-400 px-2 py-1.5 w-36">財物損失</th>
                    <th className="border border-slate-400 px-2 py-1.5 w-20">影響政府運作</th>
                  </tr>
                </thead>
                <tbody>
                  {report.impact_scale.map((item) => (
                    <tr key={item.level}>
                      <td className="border border-slate-400 px-2 py-1.5 text-center font-bold">{item.level}</td>
                      <td className="border border-slate-400 px-2 py-1.5 text-center">{item.label}</td>
                      <td className="border border-slate-400 px-2 py-1.5">{item.image}</td>
                      <td className="border border-slate-400 px-2 py-1.5 text-center">{item.personnel}</td>
                      <td className="border border-slate-400 px-2 py-1.5">{item.protest}</td>
                      <td className="border border-slate-400 px-2 py-1.5">{item.property_loss}</td>
                      <td className="border border-slate-400 px-2 py-1.5 text-center">
                        {item.government_operation}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* 免責與來源 */}
          <section className="space-y-2 border-t border-slate-200 pt-4">
            <h2 className="text-base font-bold text-slate-900">肆、資料來源與免責聲明</h2>
            <p className="text-xs text-slate-600 leading-relaxed">{report.disclaimer}</p>
            {report.source_urls.length > 0 && (
              <ul className="text-xs text-slate-500 list-disc pl-5 space-y-0.5 break-all">
                {report.source_urls.map((url) => (
                  <li key={url}>{url}</li>
                ))}
              </ul>
            )}
            <p className="text-[11px] text-slate-500">
              格式依據：教育部風險管理推動作業原則 附件二（風險可能性／影響程度評量標準表）、附件三（風險判斷基準及其風險容忍度）、附件四（現有(殘餘)風險圖像）、附件七（風險評估及處理彙總表）。
            </p>
          </section>
        </div>
      )}
    </div>
  );
};
