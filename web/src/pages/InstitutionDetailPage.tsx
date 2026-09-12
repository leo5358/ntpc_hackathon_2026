import React from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, AlertCircle, FileText, MessageSquare, ShieldAlert } from "lucide-react";

export const InstitutionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

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

      {/* Header Info */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
              非營利園
            </span>
            <span className="text-xs text-slate-400 font-mono">ID: {id || "N/A"}</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">幼兒園機構詳情骨架</h1>
          <p className="text-sm text-slate-500 mt-0.5">營運受託單位: 未指定</p>
        </div>

        <div className="flex items-center space-x-4">
          <div className="text-right">
            <span className="text-xs text-slate-500 uppercase tracking-wider block">綜合風險評分</span>
            <span className="text-3xl font-extrabold text-blue-600">--</span>
          </div>
        </div>
      </div>

      {/* Grid of Sections (Skeletons) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SHAP Breakdown Panel */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-5 h-5 text-blue-600" />
            <h2 className="text-lg font-bold text-slate-800">風險成因拆解 (SHAP Waterfall)</h2>
          </div>
          <div className="h-48 bg-slate-50 rounded-lg flex items-center justify-center text-slate-400 text-sm">
            [SHAP 歸因圖表骨架占位]
          </div>
        </div>

        {/* Budget vs Actual Drilldown */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center space-x-2">
            <FileText className="w-5 h-5 text-blue-600" />
            <h2 className="text-lg font-bold text-slate-800">預算 vs 決算執行率</h2>
          </div>
          <div className="h-48 bg-slate-50 rounded-lg flex items-center justify-center text-slate-400 text-sm">
            [預算決算科目條狀圖骨架占位]
          </div>
        </div>

        {/* Penalty Timeline */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-amber-600" />
            <h2 className="text-lg font-bold text-slate-800">歷史裁罰歷程</h2>
          </div>
          <div className="h-48 bg-slate-50 rounded-lg flex items-center justify-center text-slate-400 text-sm">
            [裁罰紀錄時間軸骨架占位]
          </div>
        </div>

        {/* Opinion Panel */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center space-x-2">
            <MessageSquare className="w-5 h-5 text-indigo-600" />
            <h2 className="text-lg font-bold text-slate-800">輿情與社群信號</h2>
          </div>
          <div className="h-48 bg-slate-50 rounded-lg flex flex-col items-center justify-center text-slate-400 text-sm space-y-2">
            <p className="text-slate-600 font-medium">無輿情資料</p>
            <p className="text-xs text-slate-400">目前公開社群與新聞查無針對本機構的近期討論</p>
          </div>
        </div>
      </div>
    </div>
  );
};
