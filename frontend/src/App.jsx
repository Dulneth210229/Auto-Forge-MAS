import { Route, Routes } from "react-router-dom";
import AppShell from "./components/layout/AppShell";
import ProjectListPage from "./pages/ProjectListPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import FeatureDetailPage from "./pages/FeatureDetailPage";
import LlmSettingsPage from "./pages/LlmSettingsPage";
import NotFoundPage from "./pages/NotFoundPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<ProjectListPage />} />
        <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
        <Route path="/projects/:projectId/features/:featureId" element={<FeatureDetailPage />} />
        <Route path="/settings/llm" element={<LlmSettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
