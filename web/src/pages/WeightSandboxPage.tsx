import React from "react";
import { Sliders, RotateCcw, Play } from "lucide-react";

export const WeightSandboxPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">動態權重模擬沙盒 (What-If Sandbox)</h1>
        <p className="text-sm text-slate-500 mt-1">
          即時調整五大指標面向之加權比例，動態重算各幼兒園風險總分與排名變化
        </p>
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
              disabled
              className="text-xs text-slate-400 hover:text-slate-600 flex items-center space-x-1 cursor-not-allowed"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>還原預設</span>
            </button>
          </div>

          <div className="space-y-5">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium text-slate-700">歷史裁罰預測 (Penalty XGB)</span>
                <span className="font-mono text-blue-600 font-semibold">45%</span>
              </div>
              <input type="range" min="0" max="100" defaultValue="45" disabled className="w-full" />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium text-slate-700">預決算殘差偏差 (Residual Z)</span>
                <span className="font-mono text-blue-600 font-semibold">20%</span>
              </div>
              <input type="range" min="0" max="100" defaultValue="20" disabled className="w-full" />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium text-slate-700">孤立森林異常度 (Isolation Forest)</span>
                <span className="font-mono text-blue-600 font-semibold">15%</span>
              </div>
              <input type="range" min="0" max="100" defaultValue="15" disabled className="w-full" />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium text-slate-700">外部輿情風險 (Opinion Risk)</span>
                <span className="font-mono text-blue-600 font-semibold">10%</span>
              </div>
              <input type="range" min="0" max="100" defaultValue="10" disabled className="w-full" />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium text-slate-700">特定規則旗標 (Rule Flags)</span>
                <span className="font-mono text-blue-600 font-semibold">10%</span>
              </div>
              <input type="range" min="0" max="100" defaultValue="10" disabled className="w-full" />
            </div>
          </div>

          <button
            disabled
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 px-4 rounded-lg flex items-center justify-center space-x-2 transition opacity-60 cursor-not-allowed"
          >
            <Play className="w-4 h-4" />
            <span>執行即時重算 (POST /api/whatif)</span>
          </button>
        </div>

        {/* Rescored Ranking Preview Skeleton */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-base font-bold text-slate-800">試算結果與排名升降預覽</h2>
          <div className="h-80 bg-slate-50 rounded-lg flex flex-col items-center justify-center text-slate-400 text-sm space-y-2">
            <p className="font-medium text-slate-600">[What-If 模擬結果比較表格骨架占位]</p>
            <p className="text-xs text-slate-400">當前為 Infra 結構階段，後續將連接後端模擬引擎與 SageMaker 即時推論</p>
          </div>
        </div>
      </div>
    </div>
  );
};
