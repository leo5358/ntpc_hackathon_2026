import React from "react";
import { MapPin, Layers } from "lucide-react";

export const RiskMapPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">新北市幼兒園風險地理分佈 (Risk Map)</h1>
          <p className="text-sm text-slate-500 mt-1">
            結合開放資料 GeoJSON 座標與綜合風險模型，以色階熱度直觀辨識各行政區幼兒園風險等級
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center space-x-3 bg-white px-4 py-2 rounded-lg border border-slate-200 text-xs shadow-sm">
          <span className="text-slate-500 font-medium">風險色階:</span>
          <span className="flex items-center space-x-1">
            <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span>
            <span className="text-slate-700">低風險 (&lt;30)</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-3 h-3 rounded-full bg-amber-500 inline-block"></span>
            <span className="text-slate-700">中風險 (30-60)</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-3 h-3 rounded-full bg-rose-500 inline-block"></span>
            <span className="text-slate-700">高風險 (&gt;60)</span>
          </span>
        </div>
      </div>

      {/* Map Canvas Skeleton */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden h-[600px] relative flex items-center justify-center bg-slate-50">
        <div className="absolute top-4 left-4 z-10 bg-white/90 backdrop-blur p-3 rounded-lg border border-slate-200 shadow-sm text-xs space-y-2 max-w-xs">
          <div className="flex items-center space-x-1.5 font-semibold text-slate-800">
            <Layers className="w-4 h-4 text-blue-600" />
            <span>圖層控制 (Infra 骨架)</span>
          </div>
          <p className="text-slate-500 leading-relaxed">
            整合 <code className="text-blue-600 font-mono">preschools.json</code> 經緯度點位。支援點擊標記查看機構基本資料、裁罰歷程與 SHAP 歸因詳情。
          </p>
        </div>

        <div className="text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
          <div className="p-4 bg-blue-50 text-blue-600 rounded-full">
            <MapPin className="w-10 h-10" />
          </div>
          <p className="text-base font-semibold text-slate-700">互動式 GIS 風險地圖骨架就緒</p>
          <p className="text-xs text-slate-500 max-w-md">
            已建立地理圖層架構與色階標準。後續將引入 Leaflet / React-Leaflet 圖資底圖並對齊幼兒園座標點位。
          </p>
        </div>
      </div>
    </div>
  );
};
