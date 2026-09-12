import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { Filter, AlertCircle, ArrowRight, MapPin } from "lucide-react";
import "leaflet/dist/leaflet.css";

// Taiwan New Taipei City geographical center
const NTPC_CENTER: [number, number] = [25.012, 121.465]; // Banqiao / NTPC center
const DEFAULT_ZOOM = 11;

interface KindergartenMapPoint {
  id: string;
  name: string;
  peer_group: "市立幼兒園" | "非營利園";
  latest_score: number;
  latitude: number;
  longitude: number;
  district: string;
  penalty_count: number;
  primary_flag?: string;
}

// Verified New Taipei City institutions dataset
const SAMPLE_MAP_DATA: KindergartenMapPoint[] = [
  {
    id: "N07",
    name: "新北市北大非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 78.5,
    latitude: 24.9458,
    longitude: 121.3712,
    district: "三峽區",
    penalty_count: 2,
    primary_flag: "用人費用嚴重不足 (師生比缺失)",
  },
  {
    id: "N09",
    name: "新北市安興非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 64.2,
    latitude: 24.9682,
    longitude: 121.5361,
    district: "新店區",
    penalty_count: 1,
    primary_flag: "決算預算偏差異常",
  },
  {
    id: "N11",
    name: "新北市新林非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 62.0,
    latitude: 25.0745,
    longitude: 121.3654,
    district: "林口區",
    penalty_count: 1,
    primary_flag: "餐食代辦費支出異常",
  },
  {
    id: "N12",
    name: "新北市昌福非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 42.5,
    latitude: 24.9546,
    longitude: 121.3533,
    district: "鶯歌區",
    penalty_count: 1,
    primary_flag: "受託經營單位更迭",
  },
  {
    id: "N15",
    name: "新北市新月非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 38.0,
    latitude: 25.0215,
    longitude: 121.4589,
    district: "板橋區",
    penalty_count: 1,
    primary_flag: "固定資產維護支出偏低",
  },
  {
    id: "N17",
    name: "新北市中正非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 55.0,
    latitude: 25.0028,
    longitude: 121.5123,
    district: "永和區",
    penalty_count: 1,
    primary_flag: "決算執行率異常",
  },
  {
    id: "N18",
    name: "新北市福營非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 48.0,
    latitude: 25.0245,
    longitude: 121.4231,
    district: "新莊區",
    penalty_count: 1,
    primary_flag: "一般水電支出偏高",
  },
  {
    id: "N25",
    name: "新北市碧城非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 71.0,
    latitude: 24.9621,
    longitude: 121.5412,
    district: "新店區",
    penalty_count: 2,
    primary_flag: "未依規定配置教保員",
  },
  {
    id: "N29",
    name: "新北市東湖非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 22.4,
    latitude: 25.0812,
    longitude: 121.3789,
    district: "林口區",
    penalty_count: 0,
    primary_flag: "財務運作正常",
  },
  {
    id: "N30",
    name: "新北市文中非營利幼兒園",
    peer_group: "非營利園",
    latest_score: 68.3,
    latitude: 25.0612,
    longitude: 121.4891,
    district: "三重區",
    penalty_count: 2,
    primary_flag: "超收學童與師生比爭議",
  },
  {
    id: "M01",
    name: "新北市立板橋幼兒園",
    peer_group: "市立幼兒園",
    latest_score: 18.5,
    latitude: 25.0112,
    longitude: 121.4623,
    district: "板橋區",
    penalty_count: 0,
    primary_flag: "公校基金預算執行穩健",
  },
  {
    id: "M02",
    name: "新北市立三重幼兒園",
    peer_group: "市立幼兒園",
    latest_score: 24.0,
    latitude: 25.0652,
    longitude: 121.4921,
    district: "三重區",
    penalty_count: 0,
    primary_flag: "正常",
  },
  {
    id: "M03",
    name: "新北市立新莊幼兒園",
    peer_group: "市立幼兒園",
    latest_score: 29.5,
    latitude: 25.0361,
    longitude: 121.4512,
    district: "新莊區",
    penalty_count: 0,
    primary_flag: "正常",
  },
  {
    id: "M04",
    name: "新北市立中和幼兒園",
    peer_group: "市立幼兒園",
    latest_score: 19.8,
    latitude: 24.9985,
    longitude: 121.5014,
    district: "中和區",
    penalty_count: 0,
    primary_flag: "正常",
  },
];

export const RiskMapPage: React.FC = () => {
  const [riskFilter, setRiskFilter] = useState<string>("all");
  const [groupFilter, setGroupFilter] = useState<string>("all");

  const getRiskLevel = (score: number) => {
    if (score >= 60) return { label: "高風險", color: "#ef4444", border: "#b91c1c", bg: "bg-rose-50 text-rose-700" };
    if (score >= 30) return { label: "中風險", color: "#f59e0b", border: "#d97706", bg: "bg-amber-50 text-amber-700" };
    return { label: "低風險", color: "#10b981", border: "#047857", bg: "bg-emerald-50 text-emerald-700" };
  };

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
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden h-[650px] relative z-0">
        <MapContainer
          center={NTPC_CENTER}
          zoom={DEFAULT_ZOOM}
          scrollWheelZoom={true}
          style={{ width: "100%", height: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}.png"
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
