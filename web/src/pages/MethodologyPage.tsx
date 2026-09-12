import React from "react";
import { Info, CheckCircle2, ShieldCheck } from "lucide-react";

export const MethodologyPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Page Title */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">模型架構與評分方法論</h1>
        <p className="text-sm text-slate-500 mt-1">
          解釋性審計支援模型 (Decision Support System) 的特徵工程、評分公式與指標驗證
        </p>
      </div>

      {/* Critical Limitation Banner */}
      <div className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-r-lg">
        <div className="flex items-start">
          <Info className="w-5 h-5 text-amber-600 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <h3 className="text-sm font-semibold text-amber-800">重要使用限制與聲明</h3>
            <p className="text-xs text-amber-700 mt-1 leading-relaxed">
              本系統所輸出之綜合風險分數（Risk Score）為<strong>異常指標（Anomaly Indicator）與資源優先分配輔助依據</strong>，絕非行政裁決或違法事實之實質指控。所有高風險預警項目皆須經由專業稽查人員比對原始財務單據與現場查核後方能定案。
            </p>
          </div>
        </div>
      </div>

      {/* Composite Formula */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-5 h-5 text-blue-600" />
          <h2 className="text-lg font-bold text-slate-800">綜合評分公式 (Composite Risk Formula)</h2>
        </div>
        <div className="bg-slate-900 text-slate-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
          risk = 100 * (0.45 * p_penalty + 0.20 * norm(residual_z) + 0.15 * iso_score + 0.10 * opinion_risk + 0.10 * flag_weight_sum)
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-600">
          <div className="border border-slate-100 p-3 rounded-lg">
            <span className="font-semibold text-slate-800">0.45 p_penalty (XGBoost):</span> 監督式裁罰預測機率（基於 11/38 非營利園已知裁罰事實）
          </div>
          <div className="border border-slate-100 p-3 rounded-lg">
            <span className="font-semibold text-slate-800">0.20 norm(residual_z):</span> 預決算殘差模型（預算與決算偏離度常態化指標）
          </div>
          <div className="border border-slate-100 p-3 rounded-lg">
            <span className="font-semibold text-slate-800">0.15 iso_score (Isolation Forest):</span> 無監督群聚異常指標（適用於未標註之市立園）
          </div>
          <div className="border border-slate-100 p-3 rounded-lg">
            <span className="font-semibold text-slate-800">0.10 opinion_risk:</span> 外部社群、PTT、Google 評論等自然語言情感與議題風險度
          </div>
          <div className="border border-slate-100 p-3 rounded-lg md:col-span-2">
            <span className="font-semibold text-slate-800">0.10 flag_weight_sum:</span> 本福特定律異常、用人費用嚴重不足等規則旗標合計
          </div>
        </div>
      </div>

      {/* Model Performance Validation */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <h2 className="text-lg font-bold text-slate-800">驗證指標與黃金數據集 (Gold Set Validation)</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 bg-slate-50 rounded-lg text-center">
            <span className="text-xs text-slate-500 block">Parser 驗證率</span>
            <span className="text-2xl font-bold text-slate-800 mt-1 block">&gt; 95%</span>
            <span className="text-xs text-emerald-600 flex items-center justify-center mt-1">
              <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> 自動對帳校驗
            </span>
          </div>
          <div className="p-4 bg-slate-50 rounded-lg text-center">
            <span className="text-xs text-slate-500 block">裁罰預測 AUC (Grouped CV)</span>
            <span className="text-2xl font-bold text-slate-800 mt-1 block">0.82 ± 0.06</span>
            <span className="text-xs text-slate-500 block mt-1">Bootstrap 區間評估</span>
          </div>
          <div className="p-4 bg-slate-50 rounded-lg text-center">
            <span className="text-xs text-slate-500 block">輿情分類 Macro-F1 (Gold Set)</span>
            <span className="text-2xl font-bold text-slate-800 mt-1 block">0.78</span>
            <span className="text-xs text-slate-500 block mt-1">400 句人工雙標標註</span>
          </div>
        </div>
      </div>
    </div>
  );
};
