import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  AlertCircle,
  FileText,
  MessageSquare,
  ShieldAlert,
  RotateCw,
  Calendar,
  DollarSign,
  TrendingUp,
  CheckCircle2,
  ExternalLink,
  Sparkles,
} from "lucide-react";
import { api } from "../services/api";
import {
  InstitutionDetail,
  AccountStatementResponse,
  OpinionResponse,
} from "../types/api";
import { getRiskLevel } from "../data/institutions";

export const InstitutionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<InstitutionDetail | null>(null);
  const [accounts, setAccounts] = useState<AccountStatementResponse | null>(null);
  const [opinion, setOpinion] = useState<OpinionResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [crawling, setCrawling] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const [detailRes, accountsRes, opinionRes] = await Promise.all([
        api.getInstitutionDetail(id),
        api.getAccounts(id, 112).catch(() => null),
        api.getOpinion(id).catch(() => null),
      ]);
      setDetail(detailRes);
      setAccounts(accountsRes);
      setOpinion(opinionRes);
    } catch (err: any) {
      setError(err?.message || "無法載入機構詳情，請確認機構代碼與後端狀態");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [id]);

  const handleLiveCrawl = async () => {
    if (!id || crawling) return;
    setCrawling(true);
    try {
      const freshOpinion = await api.getOpinion(id, true);
      setOpinion(freshOpinion);
    } catch (err) {
      console.error("Failed to refresh opinion:", err);
    } finally {
      setCrawling(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center text-slate-400 flex flex-col items-center justify-center space-y-4">
        <RotateCw className="w-10 h-10 text-blue-500 animate-spin" />
        <p className="text-base text-slate-600 font-medium">正在取得機構詳細指標、財務決算與歷史裁罰歷程...</p>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="space-y-4">
        <Link
          to="/"
          className="inline-flex items-center space-x-1.5 text-sm font-medium text-slate-500 hover:text-slate-800 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>返回風險排行</span>
        </Link>
        <div className="bg-white p-8 rounded-xl border border-rose-200 text-center space-y-3">
          <AlertCircle className="w-10 h-10 text-rose-500 mx-auto" />
          <h2 className="text-lg font-bold text-slate-800">載入失敗</h2>
          <p className="text-sm text-slate-500">{error || "查無此機構代碼"}</p>
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
          >
            重新整理
          </button>
        </div>
      </div>
    );
  }

  const risk = getRiskLevel(detail.latest_score);

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div>
        <Link
          to="/"
          className="inline-flex items-center space-x-1.5 text-sm font-medium text-slate-500 hover:text-slate-800 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>返回風險排行</span>
        </Link>
      </div>

      {/* Header Info Banner */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div className="space-y-1.5">
          <div className="flex items-center space-x-2">
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                detail.peer_group === "市立幼兒園"
                  ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                  : "bg-blue-100 text-blue-800 border border-blue-300"
              }`}
            >
              {detail.peer_group}
            </span>
            <span className="text-xs text-slate-400 font-mono">ID: {detail.id}</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900">{detail.name}</h1>
          <p className="text-sm text-slate-500">
            營運受託單位: <span className="font-medium text-slate-700">{detail.operator || "公立公營"}</span>
          </p>
        </div>

        <div className="flex items-center space-x-6">
          <div className="text-right">
            <span className="text-xs text-slate-500 uppercase tracking-wider block">綜合風險評分</span>
            <div className="flex items-baseline space-x-2 justify-end">
              <span className="text-4xl font-black font-mono" style={{ color: risk.color }}>
                {detail.latest_score}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${risk.bg}`}>
                {risk.label}
              </span>
            </div>
          </div>
          <Link
            to={`/report/${detail.id}`}
            className="inline-flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2.5 rounded-lg text-sm font-medium transition shadow-sm"
          >
            <FileText className="w-4 h-4" />
            <span>產製風險彙總表</span>
          </Link>
        </div>
      </div>

      {/* Score History Strip */}
      {detail.history && detail.history.length > 0 && (
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center space-x-2 mb-3">
            <TrendingUp className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-800">近三年風險評分與裁罰機率演變</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {detail.history.map((h) => (
              <div
                key={h.academic_year}
                className="bg-slate-50 p-3 rounded-lg border border-slate-200 flex justify-between items-center"
              >
                <div>
                  <span className="text-xs font-semibold text-slate-500 block">{h.academic_year}學年度</span>
                  <span className="text-xs text-slate-400">裁罰預測機率: {(h.p_penalty * 100).toFixed(0)}%</span>
                </div>
                <span className="text-xl font-bold font-mono text-slate-800">{h.score}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grid of Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SHAP Breakdown Panel */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-5 h-5 text-blue-600" />
            <div>
              <h2 className="text-base font-bold text-slate-800">風險成因拆解 (SHAP Feature Attribution)</h2>
              <p className="text-xs text-slate-400">各特徵變數對機構風險評分之正負推升貢獻</p>
            </div>
          </div>

          {detail.shap_breakdown && detail.shap_breakdown.length > 0 ? (
            <div className="space-y-3 pt-2">
              {detail.shap_breakdown.map((item, idx) => {
                const isPositive = item.contribution > 0;
                const absPct = Math.min(100, Math.abs(item.contribution) * 150);
                return (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between text-xs font-medium">
                      <span className="text-slate-700">{item.label_zh}</span>
                      <span
                        className={`font-mono font-bold ${
                          isPositive ? "text-rose-600" : "text-emerald-600"
                        }`}
                      >
                        {isPositive ? "+" : ""}
                        {item.contribution.toFixed(2)}
                      </span>
                    </div>
                    <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden flex">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          isPositive ? "bg-rose-500" : "bg-emerald-500"
                        }`}
                        style={{ width: `${absPct}%` }}
                      />
                    </div>
                    {item.value && (
                      <span className="text-[11px] text-slate-400 block">數值佐證: {String(item.value)}</span>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="h-40 bg-slate-50 rounded-lg flex items-center justify-center text-slate-400 text-sm">
              各項指標均在正常常態分布區間，無單一顯著推升因子
            </div>
          )}
        </div>

        {/* Budget vs Actual Drilldown */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center space-x-2">
            <DollarSign className="w-5 h-5 text-emerald-600" />
            <div>
              <h2 className="text-base font-bold text-slate-800">預算 vs 決算執行科目明細</h2>
              <p className="text-xs text-slate-400">112年度會計科目執行率與偏差驗證</p>
            </div>
          </div>

          {accounts && accounts.items && accounts.items.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-slate-500 uppercase">
                    <th className="py-2 px-3">會計科目</th>
                    <th className="py-2 px-3 text-right">預算數</th>
                    <th className="py-2 px-3 text-right">決算數</th>
                    <th className="py-2 px-3 text-right">執行偏差</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {accounts.items.map((acc, idx) => {
                    const isAbnormal = acc.variance_pct !== undefined && Math.abs(acc.variance_pct) > 20;
                    return (
                      <tr key={idx} className="hover:bg-slate-50/70">
                        <td className="py-2.5 px-3 font-medium text-slate-800">
                          {acc.account_name}
                          <span className="text-[10px] text-slate-400 block font-mono">#{acc.account_code}</span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                          ${acc.budget.toLocaleString()}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-slate-800 font-semibold">
                          ${acc.actual.toLocaleString()}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[11px] font-bold ${
                              isAbnormal
                                ? "bg-rose-100 text-rose-700"
                                : "bg-slate-100 text-slate-600"
                            }`}
                          >
                            {acc.variance_pct !== undefined
                              ? `${acc.variance_pct > 0 ? "+" : ""}${acc.variance_pct}%`
                              : `${acc.variance > 0 ? "+" : ""}${acc.variance.toLocaleString()}`}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="h-40 bg-slate-50 rounded-lg flex items-center justify-center text-slate-400 text-sm">
              公校基金財務科目按期核銷，無重大異常差額科目
            </div>
          )}
        </div>

        {/* Penalty Timeline */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-amber-600" />
            <div>
              <h2 className="text-base font-bold text-slate-800">歷史裁罰歷程</h2>
              <p className="text-xs text-slate-400">教育部全國教保資訊網公開之行政處分案</p>
            </div>
          </div>

          {detail.penalties && detail.penalties.length > 0 ? (
            <div className="space-y-4 pt-1">
              {detail.penalties.map((pen, idx) => (
                <div
                  key={idx}
                  className="relative pl-6 pb-2 border-l-2 border-amber-300 last:border-l-0"
                >
                  <div className="absolute -left-[7px] top-0 w-3 h-3 rounded-full bg-amber-500 ring-4 ring-white" />
                  <div className="bg-amber-50/60 p-3 rounded-lg border border-amber-200/80 space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-800 flex items-center space-x-1.5">
                        <Calendar className="w-3.5 h-3.5 text-amber-600" />
                        <span>{pen.date}</span>
                      </span>
                      {pen.fine_ntd > 0 && (
                        <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-rose-100 text-rose-700">
                          罰鍰 ${pen.fine_ntd.toLocaleString()}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-700 font-medium">{pen.violation}</p>
                    <div className="text-[11px] text-slate-400 flex flex-wrap gap-2 pt-0.5">
                      <span>依據法條: {pen.law}</span>
                      <span>文號: {pen.doc_no}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-40 bg-emerald-50/60 border border-emerald-200 rounded-lg flex flex-col items-center justify-center text-emerald-700 text-sm space-y-1">
              <CheckCircle2 className="w-8 h-8 text-emerald-600" />
              <p className="font-semibold">近三年無任何違規裁罰紀錄</p>
              <p className="text-xs text-emerald-600/80">恪遵教保服務人員條例與幼照法規範</p>
            </div>
          )}
        </div>

        {/* Opinion Panel */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <MessageSquare className="w-5 h-5 text-indigo-600" />
              <div>
                <h2 className="text-base font-bold text-slate-800">外部輿情與社群信號</h2>
                <p className="text-xs text-slate-400">AWS Bedrock Claude 語意分析與論壇熱度</p>
              </div>
            </div>
            <button
              onClick={handleLiveCrawl}
              disabled={crawling}
              className="inline-flex items-center space-x-1 text-xs text-blue-600 hover:text-blue-700 bg-blue-50 px-2.5 py-1.5 rounded transition disabled:opacity-50"
              title="即時爬取社群並由 Bedrock 重新分析"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{crawling ? "分析中..." : "即時重測"}</span>
            </button>
          </div>

          {opinion && opinion.has_opinion && opinion.documents && opinion.documents.length > 0 ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between bg-slate-50 p-3 rounded-lg text-xs">
                <div>
                  <span className="text-slate-500">社群討論筆數:</span>{" "}
                  <span className="font-bold text-slate-800">{opinion.coverage} 則</span>
                </div>
                <div>
                  <span className="text-slate-500">情緒極性指數:</span>{" "}
                  <span
                    className={`font-mono font-bold ${
                      opinion.opinion_risk > 0.5 ? "text-rose-600" : "text-slate-700"
                    }`}
                  >
                    {opinion.opinion_risk.toFixed(2)}
                  </span>
                </div>
              </div>

              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {opinion.documents.map((doc) => (
                  <div key={doc.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-semibold text-slate-700">{doc.source}</span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-indigo-100 text-indigo-700">
                        {doc.topic}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 line-clamp-2">{doc.snippet}</p>
                    {doc.url && (
                      <a
                        href={doc.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center space-x-1 text-[11px] text-blue-600 hover:underline"
                      >
                        <span>查看原文</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="h-40 bg-slate-50 rounded-lg flex flex-col items-center justify-center text-slate-400 text-sm space-y-2">
              <p className="text-slate-600 font-medium">目前查無負面社群輿情</p>
              <p className="text-xs text-slate-400 text-center max-w-xs">
                Google 評論、PTT、Dcard 與新聞均未發現重大陳情或安全爭議貼文
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

