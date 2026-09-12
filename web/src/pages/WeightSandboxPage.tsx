import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Sliders,
  RotateCcw,
  Play,
  TrendingUp,
  TrendingDown,
  Minus,
  RotateCw,
  AlertCircle,
} from "lucide-react";
import { api } from "../services/api";
import { RescoredItem, WhatIfRequest } from "../types/api";

const DEFAULT_WEIGHTS = {
  penalty: 45,
  residual: 20,
  isolation_forest: 15,
  opinion: 10,
  flags: 10,
};

export const WeightSandboxPage: React.FC = () => {
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const [academicYear, setAcademicYear] = useState<number>(112);
  const [items, setItems] = useState<RescoredItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const totalWeight =
    weights.penalty +
    weights.residual +
    weights.isolation_forest +
    weights.opinion +
    weights.flags;

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload: WhatIfRequest = {
        weights: {
          penalty: weights.penalty / 100,
          residual: weights.residual / 100,
          isolation_forest: weights.isolation_forest / 100,
          opinion: weights.opinion / 100,
          flags: weights.flags / 100,
        },
        academic_year: academicYear,
      };
      const res = await api.postWhatIf(payload);
      setItems(res.items);
    } catch (err: any) {
      setError(err?.message || "模擬計算失敗，請確認後端服務正常");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runSimulation();
  }, [academicYear]);

  const handleReset = () => {
    setWeights(DEFAULT_WEIGHTS);
  };

  const handleWeightChange = (key: keyof typeof DEFAULT_WEIGHTS, val: number) => {
    setWeights((prev) => ({ ...prev, [key]: val }));
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">動態權重模擬沙盒 (What-If Sandbox)</h1>
          <p className="text-sm text-slate-500 mt-1">
            即時調整五大指標面向之加權比例，動態重算各幼兒園風險總分與排名變化，輔助稽核策略情境模擬
          </p>
        </div>
        <div className="flex items-center space-x-2 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-sm text-sm">
          <span className="font-medium text-slate-700">基準學年度:</span>
          <select
            value={academicYear}
            onChange={(e) => setAcademicYear(Number(e.target.value))}
            className="bg-slate-50 border border-slate-300 rounded px-2 py-1 text-sm font-semibold text-blue-600 focus:outline-none"
          >
            <option value="112">112學年度</option>
            <option value="111">111學年度</option>
            <option value="110">110學年度</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sliders Configuration Panel */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-800 flex items-center space-x-2">
              <Sliders className="w-5 h-5 text-blue-600" />
              <span>權重參數調整</span>
            </h2>
            <button
              onClick={handleReset}
              className="text-xs text-blue-600 hover:text-blue-800 flex items-center space-x-1 font-medium transition"
              title="重設為系統基準權重"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>還原預設</span>
            </button>
          </div>

          <div className="space-y-5">
            <div>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="font-medium text-slate-700">歷史裁罰預測 (Penalty Prob)</span>
                <span className="font-mono text-blue-600 font-semibold">{weights.penalty}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={weights.penalty}
                onChange={(e) => handleWeightChange("penalty", Number(e.target.value))}
                className="w-full accent-blue-600 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="font-medium text-slate-700">預決算殘差偏差 (Residual Z)</span>
                <span className="font-mono text-blue-600 font-semibold">{weights.residual}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={weights.residual}
                onChange={(e) => handleWeightChange("residual", Number(e.target.value))}
                className="w-full accent-blue-600 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="font-medium text-slate-700">孤立森林異常度 (Isolation Forest)</span>
                <span className="font-mono text-blue-600 font-semibold">{weights.isolation_forest}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={weights.isolation_forest}
                onChange={(e) => handleWeightChange("isolation_forest", Number(e.target.value))}
                className="w-full accent-blue-600 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="font-medium text-slate-700">外部輿情風險 (Opinion Risk)</span>
                <span className="font-mono text-blue-600 font-semibold">{weights.opinion}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={weights.opinion}
                onChange={(e) => handleWeightChange("opinion", Number(e.target.value))}
                className="w-full accent-blue-600 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="font-medium text-slate-700">特定規則旗標 (Rule Flags)</span>
                <span className="font-mono text-blue-600 font-semibold">{weights.flags}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={weights.flags}
                onChange={(e) => handleWeightChange("flags", Number(e.target.value))}
                className="w-full accent-blue-600 cursor-pointer"
              />
            </div>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs flex justify-between items-center">
            <span className="text-slate-500">權重合計比率:</span>
            <span
              className={`font-mono font-bold ${
                totalWeight === 100 ? "text-emerald-600" : "text-amber-600"
              }`}
            >
              {totalWeight}% (後端自動正規化計算)
            </span>
          </div>

          <button
            onClick={runSimulation}
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 px-4 rounded-lg flex items-center justify-center space-x-2 transition shadow-sm disabled:opacity-50"
          >
            {loading ? (
              <>
                <RotateCw className="w-4 h-4 animate-spin" />
                <span>模擬重算中...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                <span>執行即時重算 (POST /api/whatif)</span>
              </>
            )}
          </button>
        </div>

        {/* Rescored Ranking Preview */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-800">試算結果與排名升降預覽</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                依自訂權重模擬計算後之最新風險分數，對比原預設基準排名之位移幅度
              </p>
            </div>
            <span className="text-xs font-medium text-slate-500 bg-slate-100 px-2.5 py-1 rounded">
              共 {items.length} 所機構
            </span>
          </div>

          {error ? (
            <div className="p-8 text-center text-rose-500 flex flex-col items-center justify-center space-y-2">
              <AlertCircle className="w-8 h-8 text-rose-500" />
              <p className="text-sm font-semibold">{error}</p>
            </div>
          ) : items.length === 0 ? (
            <div className="h-80 bg-slate-50 rounded-lg flex items-center justify-center text-slate-400 text-sm">
              點擊「執行即時重算」產生模擬預覽
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/80 text-slate-500 text-xs uppercase">
                    <th className="py-2.5 px-3 w-16 text-center">新名次</th>
                    <th className="py-2.5 px-3">機構名稱</th>
                    <th className="py-2.5 px-3 text-right">基準分數</th>
                    <th className="py-2.5 px-3 text-right">模擬分數</th>
                    <th className="py-2.5 px-3 text-right">分數增減</th>
                    <th className="py-2.5 px-3 text-center w-28">名次升降</th>
                    <th className="py-2.5 px-3 text-right">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs">
                  {items.map((item, idx) => {
                    const newRank = idx + 1;
                    const diff = Number((item.new_score - item.original_score).toFixed(1));
                    return (
                      <tr key={item.id} className="hover:bg-slate-50/70">
                        <td className="py-3 px-3 text-center font-bold text-slate-700">
                          {newRank}
                        </td>
                        <td className="py-3 px-3">
                          <Link
                            to={`/institutions/${item.id}`}
                            className="font-semibold text-slate-900 hover:text-blue-600 transition"
                          >
                            {item.name}
                          </Link>
                          <span className="text-[11px] text-slate-400 font-mono block">ID: {item.id}</span>
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-slate-600">
                          {item.original_score}
                        </td>
                        <td className="py-3 px-3 text-right font-mono font-bold text-slate-900">
                          {item.new_score}
                        </td>
                        <td className="py-3 px-3 text-right font-mono">
                          <span
                            className={
                              diff > 0
                                ? "text-rose-600 font-semibold"
                                : diff < 0
                                ? "text-emerald-600 font-semibold"
                                : "text-slate-400"
                            }
                          >
                            {diff > 0 ? `+${diff}` : diff}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-center">
                          {item.rank_change > 0 ? (
                            <span className="inline-flex items-center space-x-0.5 text-rose-600 font-bold bg-rose-50 px-2 py-0.5 rounded">
                              <TrendingUp className="w-3 h-3" />
                              <span>上升 {item.rank_change}</span>
                            </span>
                          ) : item.rank_change < 0 ? (
                            <span className="inline-flex items-center space-x-0.5 text-emerald-600 font-bold bg-emerald-50 px-2 py-0.5 rounded">
                              <TrendingDown className="w-3 h-3" />
                              <span>下降 {Math.abs(item.rank_change)}</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center space-x-0.5 text-slate-400">
                              <Minus className="w-3 h-3" />
                              <span>持平</span>
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-right">
                          <Link
                            to={`/report/${item.id}`}
                            className="text-blue-600 hover:text-blue-800 font-medium"
                          >
                            報表
                          </Link>
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
    </div>
  );
};

