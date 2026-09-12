import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { RankingPage } from "./pages/RankingPage";
import { RiskMapPage } from "./pages/RiskMapPage";
import { InstitutionDetailPage } from "./pages/InstitutionDetailPage";
import { MethodologyPage } from "./pages/MethodologyPage";
import { WeightSandboxPage } from "./pages/WeightSandboxPage";
import { RiskReportPage } from "./pages/RiskReportPage";
import { CityRiskReportPage } from "./pages/CityRiskReportPage";

export const App: React.FC = () => {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<RankingPage />} />
          <Route path="map" element={<RiskMapPage />} />
          <Route path="i/:id" element={<InstitutionDetailPage />} />
          <Route path="report" element={<CityRiskReportPage />} />
          <Route path="report/city" element={<CityRiskReportPage />} />
          <Route path="report/:id" element={<RiskReportPage />} />
          <Route path="method" element={<MethodologyPage />} />
          <Route path="sandbox" element={<WeightSandboxPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
