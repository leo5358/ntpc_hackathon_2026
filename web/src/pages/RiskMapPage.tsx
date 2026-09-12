import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import { Filter, AlertCircle, ArrowRight, MapPin } from "lucide-react";
import "leaflet/dist/leaflet.css";

import { SAMPLE_MAP_DATA, getRiskLevel } from "../data/institutions";

// Taiwan New Taipei City geographical center
const NTPC_CENTER: [number, number] = [25.012, 121.465]; // Banqiao / NTPC center
const DEFAULT_ZOOM = 11;

/**
 * Component to ensure Leaflet recalculates dimensions after initial render
 * or route navigation transition.
 */
const MapResizer: React.FC = () => {
  const map = useMap();
  useEffect(() => {
    map.invalidateSize();
    const t1 = setTimeout(() => map.invalidateSize(), 150);
    const t2 = setTimeout(() => map.invalidateSize(), 500);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [map]);
  return null;
};


export const RiskMapPage: React.FC = () => {
  const [riskFilter, setRiskFilter] = useState<string>("all");
  const [groupFilter, setGroupFilter] = useState<string>("all");

  const filteredSchools = useMemo(() => {
    return SAMPLE_MAP_DATA.filter((s) => {
      if (groupFilter !== "all" && s.peer_group !== groupFilter) return false;
      if (riskFilter === "high" && s.latest_score < 60) return false;
      if (riskFilter === "medium" && (s.latest_score < 30 || s.latest_score >= 60)) return false;
      if (riskFilter === "low" && s.latest_score >= 30) return false;
      return true;
    });
  }, [riskFilter, groupFilter]);

  const stats = useMemo(() => {
    const total = filteredSchools.length;
    const high = filteredSchools.filter((s) => s.latest_score >= 60).length;
    const avg = total > 0 ? (filteredSchools.reduce((acc, cur) => acc + cur.latest_score, 0) / total).toFixed(1) : "0";
    return { total, high, avg };
  }, [filteredSchools]);

  return (
    <div className="space-y-6">
      {/* Page Header & Legend */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
            <MapPin className="w-7 h-7 text-blue-600" />
            <span>新北市幼兒園風險地理分佈 (GIS Risk Map)</span>
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            結合開放圖資與綜合評分模型，透過顏色深度直觀辨識各行政區幼兒園風險等級，輔助稽查巡檢排程
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center space-x-4 bg-white px-4 py-2.5 rounded-xl border border-slate-200 text-xs shadow-sm">
          <span className="text-slate-500 font-semibold">風險色階:</span>
          <span className="flex items-center space-x-1.5">
            <span className="w-3.5 h-3.5 rounded-full bg-rose-500 border border-rose-600 inline-block"></span>
            <span className="text-slate-700 font-medium">高風險 (&ge;60)</span>
          </span>
          <span className="flex items-center space-x-1.5">
            <span className="w-3.5 h-3.5 rounded-full bg-amber-500 border border-amber-600 inline-block"></span>
            <span className="text-slate-700 font-medium">中風險 (30-59)</span>
          </span>
          <span className="flex items-center space-x-1.5">
            <span className="w-3.5 h-3.5 rounded-full bg-emerald-500 border border-emerald-600 inline-block"></span>
            <span className="text-slate-700 font-medium">低風險 (&lt;30)</span>
          </span>
        </div>
      </div>

      {/* Filter & Metric Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <span className="text-sm font-medium text-slate-700">風險等級:</span>
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="bg-slate-50 border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">全部風險等級</option>
              <option value="high">僅高風險 (&ge;60)</option>
              <option value="medium">僅中風險 (30-59)</option>
              <option value="low">僅低風險 (&lt;30)</option>
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-slate-700">機構群組:</span>
            <select
              value={groupFilter}
              onChange={(e) => setGroupFilter(e.target.value)}
              className="bg-slate-50 border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">全部群組</option>
              <option value="非營利園">非營利園</option>
              <option value="市立幼兒園">市立幼兒園</option>
            </select>
          </div>
        </div>

        {/* Quick Stats Pill */}
        <div className="flex items-center space-x-4 text-xs">
          <span className="text-slate-500">
            顯示校數: <strong className="text-slate-800 text-sm font-bold">{stats.total}</strong>
          </span>
          <span className="text-rose-600">
            高風險警戒: <strong className="text-rose-600 text-sm font-bold">{stats.high}</strong>
          </span>
          <span className="text-blue-600">
            平均風險值: <strong className="text-blue-600 text-sm font-bold">{stats.avg}</strong>
          </span>
        </div>
      </div>

      {/* Map Canvas */}
      <div
        className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden relative"
        style={{ height: "650px", minHeight: "550px", width: "100%" }}
      >
        <MapContainer
          center={NTPC_CENTER}
          zoom={DEFAULT_ZOOM}
          scrollWheelZoom={true}
          style={{ width: "100%", height: "100%", minHeight: "550px" }}
        >
          <MapResizer />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
            subdomains={["a", "b", "c", "d"]}
            maxZoom={19}
            crossOrigin="anonymous"
          />

          {filteredSchools.map((school) => {
            const riskInfo = getRiskLevel(school.latest_score);

            return (
              <CircleMarker
                key={school.id}
                center={[school.latitude, school.longitude]}
                radius={school.latest_score >= 60 ? 11 : 9}
                pathOptions={{
                  color: riskInfo.border,
                  fillColor: riskInfo.color,
                  fillOpacity: 0.85,
                  weight: 2.5,
                }}
              >
                <Popup>
                  <div className="p-1 min-w-[220px] space-y-2 text-slate-800">
                    <div className="flex items-center justify-between gap-2 border-b border-slate-100 pb-1.5">
                      <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 font-medium text-slate-600">
                        {school.peer_group} · {school.district}
                      </span>
                      <span
                        className="text-xs font-bold px-2 py-0.5 rounded text-white shadow-xs"
                        style={{ backgroundColor: riskInfo.color }}
                      >
                        風險 {school.latest_score}
                      </span>
                    </div>

                    <div>
                      <h4 className="font-bold text-sm text-slate-900 leading-tight">{school.name}</h4>
                      <p className="text-[11px] text-slate-500 mt-0.5 font-mono">編號: {school.id}</p>
                    </div>

                    <div className="bg-slate-50 p-2 rounded text-xs space-y-1">
                      <div className="flex justify-between">
                        <span className="text-slate-500">歷史裁罰:</span>
                        <span className="font-semibold text-rose-600">{school.penalty_count} 次</span>
                      </div>
                      {school.primary_flag && (
                        <div className="text-[11px] text-amber-700 flex items-start space-x-1 mt-1">
                          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                          <span>{school.primary_flag}</span>
                        </div>
                      )}
                    </div>

                    <Link
                      to={`/i/${school.id}`}
                      className="inline-flex items-center justify-center w-full space-x-1 text-xs bg-blue-600 hover:bg-blue-700 text-white font-medium py-1.5 px-3 rounded transition mt-1"
                    >
                      <span>檢視完整審計報告</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
};
