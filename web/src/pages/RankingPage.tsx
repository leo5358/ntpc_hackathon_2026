import { FileText, Filter, Search, AlertTriangle, MapPin } from "lucide-react";
import { Link } from "react-router-dom";

export const RankingPage: React.FC = () => {
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
        </div>
      </div>

      {/* Filter Bar (UI Skeleton) */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center gap-4">
        <div className="flex items-center space-x-2 min-w-[180px]">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-medium text-slate-700">學年度:</span>
          <select className="bg-slate-50 border border-slate-300 rounded-md px-3 py-1.5 text-sm focus:outline-none">
            <option value="112">112學年度</option>
            <option value="111">111學年度</option>
            <option value="110">110學年度</option>
          </select>
        </div>

        <div className="flex items-center space-x-2 min-w-[200px]">
          <span className="text-sm font-medium text-slate-700">類型:</span>
          <select className="bg-slate-50 border border-slate-300 rounded-md px-3 py-1.5 text-sm focus:outline-none">
            <option value="all">全部同儕群組</option>
            <option value="市立幼兒園">市立幼兒園</option>
            <option value="非營利園">非營利園</option>
          </select>
        </div>

        <div className="flex-1 min-w-[240px]">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="搜尋幼兒園名稱或 ID..."
              className="w-full bg-slate-50 border border-slate-300 rounded-md pl-9 pr-4 py-1.5 text-sm focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* Table Skeleton Placeholder */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-8 text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
          <AlertTriangle className="w-8 h-8 text-amber-500" />
          <p className="text-base font-medium text-slate-700">前後端 Infra 骨架已就緒</p>
          <p className="text-xs text-slate-500 max-w-md">
            此頁面已完成路由與版面結構（Ranking Table、篩選控制項、CSV 匯出按鈕）。下一步將在邏輯階段串接後端 API 呈現真實機構排名。
          </p>
        </div>
      </div>
    </div>
  );
};
