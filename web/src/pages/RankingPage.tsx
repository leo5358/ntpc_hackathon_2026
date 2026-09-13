import React, { useEffect, useState, useMemo } from "react";
import {
  FileText,
  Filter,
  Search,
  AlertTriangle,
  MapPin,
  Download,
  ChevronRight,
  MessageSquare,
  ShieldAlert,
  RotateCw,
} from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import { RankingItem } from "../types/api";
import { getRiskLevel } from "../data/institutions";

export const RankingPage: React.FC = () => {
  const [year, setYear] = useState<number>(112);
  const [group, setGroup] = useState<string>("all");
  const [minScore, setMinScore] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [items, setItems] = useState<RankingItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRankings = async () => {
    setLoading(true);
    setError(null);
    try {
      const g = group === "all" ? undefined : group;
      const min = minScore === "high" ? 60 : minScore === "medium" ? 30 : undefined;
      const res = await api.getRankings(year, g, min);
      setItems(res.items);
    } catch (err: any) {
      setError(err?.message || "無法載入排名資料，請確認後端服務已啟動");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRankings();
  }, [year, group, minScore]);

  const filteredItems = useMemo(() => {
    if (!searchQuery.trim()) return items;
    const q = searchQuery.toLowerCase().trim();
    return items.filter(
      (it) => it.name.toLowerCase().includes(q) || it.id.toLowerCase().includes(q)
    );
  }, [items, searchQuery]);

  const handleExportCSV = () => {
    if (!filteredItems.length) return;
    const headers = ["名次", "機構代碼", "機構名稱", "同儕類型", "學年度", "風險評分", "裁罰機率", "違規旗標數", "輿情信號"];
    const rows = filteredItems.map((it) => [
      it.rank,
      it.id,
      `"${it.name.replace(/"/g, '""')}"`,
      it.peer_group,
      it.academic_year,
      it.score,
      `${(it.p_penalty * 100).toFixed(1)}%`,
      it.flag_count,
      it.has_opinion ? "有" : "無",
    ]);

    const csvContent = "\uFEFF" + [headers.join(","), ...rows.map((r) => r.join(","))].join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `新北市幼兒園風險總排行_${year}學年度.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">幼兒園風險總排行</h1>
          <p className="text-sm text-slate-500 mt-1">
            基於財務決算預算偏差、歷史裁罰紀錄、輿情聲量與異常規則的綜合風險評估
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Link
            to="/map"
            className="inline-flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition shadow-sm"
          >
            <MapPin className="w-4 h-4" />
            <span>切換至地理風險地圖</span>
          </Link>
          <Link
            to="/report/city"
            className="inline-flex items-center space-x-2 bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 rounded-lg text-sm font-medium transition shadow-sm"
            title="產製全市風險評估綜整報告（含高風險機構專案報告），可列印或匯出 CSV"
          >
            <FileText className="w-4 h-4" />
            <span>產製綜整報告</span>
          </Link>
          <button
            onClick={handleExportCSV}
            disabled={filteredItems.length === 0}
            className="inline-flex items-center space-x-2 border border-slate-300 hover:bg-slate-50 text-slate-700 px-3.5 py-2 rounded-lg text-sm font-medium transition shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
            title="匯出目前列表為 CSV 檔"
          >
            <Download className="w-4 h-4" />
            <span>匯出 CSV</span>
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center gap-4">
        <div className="flex items-center space-x-2 min-w-[180px]">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-medium text-slate-700">學年度:</span>
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="bg-slate-50 border border-slate-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="112">112學年度</option>
            <option value="111">111學年度</option>
            <option value="110">110學年度</option>
          </select>
        </div>

        <div className="flex items-center space-x-2 min-w-[200px]">
          <span className="text-sm font-medium text-slate-700">類型:</span>
          <select
            value={group}
            onChange={(e) => setGroup(e.target.value)}
            className="bg-slate-50 border border-slate-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">全部同儕群組</option>
            <option value="私立幼兒園">私立幼兒園</option>
            <option value="市立幼兒園">市立幼兒園</option>
            <option value="非營利園">非營利園</option>
          </select>
        </div>

        <div className="flex items-center space-x-2 min-w-[180px]">
          <span className="text-sm font-medium text-slate-700">門檻:</span>
          <select
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            className="bg-slate-50 border border-slate-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">全部分數等級</option>
            <option value="high">高風險 (≥60)</option>
            <option value="medium">中高風險 (≥30)</option>
          </select>
        </div>

        <div className="flex-1 min-w-[240px]">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜尋幼兒園名稱或 ID..."
              className="w-full bg-slate-50 border border-slate-300 rounded-md pl-9 pr-4 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <button
          onClick={fetchRankings}
          className="p-2 text-slate-500 hover:text-blue-600 hover:bg-slate-100 rounded-lg transition"
          title="重新整理資料"
        >
          <RotateCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Table Content */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
            <RotateCw className="w-8 h-8 text-blue-500 animate-spin" />
            <p className="text-sm text-slate-600">正在向後端 API 取得最新排名與風險指標...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-rose-500 flex flex-col items-center justify-center space-y-3">
            <AlertTriangle className="w-8 h-8 text-rose-500" />
            <p className="text-sm font-semibold">{error}</p>
            <button
              onClick={fetchRankings}
              className="mt-2 px-3 py-1 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded hover:bg-rose-100"
            >
              重試連線
            </button>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <p className="text-sm">查無符合條件的幼兒園機構</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/75 text-slate-500 text-xs uppercase tracking-wider">
                  <th className="py-3 px-4 w-16 text-center">排名</th>
                  <th className="py-3 px-4">幼兒園機構</th>
                  <th className="py-3 px-4 w-28">群組類型</th>
                  <th className="py-3 px-4 w-44">綜合風險評分</th>
                  <th className="py-3 px-4 w-28 text-center">裁罰機率</th>
                  <th className="py-3 px-4 w-28 text-center">異常旗標</th>
                  <th className="py-3 px-4 w-24 text-center">輿情</th>
                  <th className="py-3 px-4 w-44 text-right">操作與報告</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-sm">
                {filteredItems.map((item) => {
                  const risk = getRiskLevel(item.score);
                  return (
                    <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                      {/* Rank badge */}
                      <td className="py-4 px-4 text-center">
                        <span
                          className={`inline-flex items-center justify-center w-7 h-7 rounded-full font-bold text-xs ${
                            item.rank === 1
                              ? "bg-amber-100 text-amber-800 border border-amber-300"
                              : item.rank === 2
                              ? "bg-slate-200 text-slate-800 border border-slate-300"
                              : item.rank === 3
                              ? "bg-orange-100 text-orange-800 border border-orange-300"
                              : "bg-slate-100 text-slate-600"
                          }`}
                        >
                          {item.rank}
                        </span>
                      </td>

                      {/* Name & ID */}
                      <td className="py-4 px-4">
                        <div className="flex flex-col">
                          <Link
                            to={`/institutions/${item.id}`}
                            className="font-semibold text-slate-900 hover:text-blue-600 transition flex items-center space-x-1"
                          >
                            <span>{item.name}</span>
                            <ChevronRight className="w-3.5 h-3.5 text-slate-400 opacity-0 hover:opacity-100" />
                          </Link>
                          <span className="text-xs text-slate-400 font-mono mt-0.5">ID: {item.id}</span>
                        </div>
                      </td>

                      {/* Peer Group */}
                      <td className="py-4 px-4">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                            item.peer_group === "市立幼兒園"
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : item.peer_group === "非營利園"
                              ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                              : "bg-purple-50 text-purple-700 border border-purple-200"
                          }`}
                        >
                          {item.peer_group}
                        </span>
                      </td>

                      {/* Score & Progress */}
                      <td className="py-4 px-4">
                        <div className="space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-900 font-mono text-sm">{item.score}</span>
                            <span
                              className={`text-[11px] px-1.5 py-0.5 rounded font-medium ${risk.bg}`}
                            >
                              {risk.label}
                            </span>
                          </div>
                          <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-300"
                              style={{
                                width: `${Math.min(100, item.score)}%`,
                                backgroundColor: risk.color,
                              }}
                            />
                          </div>
                        </div>
                      </td>

                      {/* Penalty Probability */}
                      <td className="py-4 px-4 text-center font-mono font-medium text-slate-700">
                        {(item.p_penalty * 100).toFixed(0)}%
                      </td>

                      {/* Flags */}
                      <td className="py-4 px-4 text-center">
                        {item.flag_count > 0 ? (
                          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-700">
                            <ShieldAlert className="w-3 h-3" />
                            <span>{item.flag_count} 項</span>
                          </span>
                        ) : (
                          <span className="text-xs text-slate-400 font-medium">正常</span>
                        )}
                      </td>

                      {/* Opinion */}
                      <td className="py-4 px-4 text-center">
                        {item.has_opinion ? (
                          <span className="inline-flex items-center justify-center text-blue-600" title="已有公開社群與新聞輿情資料">
                            <MessageSquare className="w-4 h-4" />
                          </span>
                        ) : (
                          <span className="text-slate-300 text-xs">-</span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="py-4 px-4 text-right">
                        <div className="inline-flex items-center space-x-2">
                          <Link
                            to={`/institutions/${item.id}`}
                            className="px-2.5 py-1 text-xs font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded transition"
                          >
                            指標分析
                          </Link>
                          <Link
                            to={`/report/${item.id}`}
                            className="px-2.5 py-1 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded transition"
                          >
                            彙總表
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

