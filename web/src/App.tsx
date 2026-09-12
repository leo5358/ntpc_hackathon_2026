import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { RankingPage } from "./pages/RankingPage";
import { InstitutionDetailPage } from "./pages/InstitutionDetailPage";
import { MethodologyPage } from "./pages/MethodologyPage";
import { WeightSandboxPage } from "./pages/WeightSandboxPage";

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<RankingPage />} />
          <Route path="i/:id" element={<InstitutionDetailPage />} />
          <Route path="method" element={<MethodologyPage />} />
          <Route path="sandbox" element={<WeightSandboxPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
