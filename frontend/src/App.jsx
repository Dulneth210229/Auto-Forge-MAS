import { Route, Routes } from "react-router-dom";
import AppShell from "./components/layout/AppShell";
import ProjectListPage from "./pages/ProjectListPage";
import ProjectWorkspacePage from "./pages/ProjectWorkspacePage";
import LlmSettingsPage from "./pages/LlmSettingsPage";
import NotFoundPage from "./pages/NotFoundPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<ProjectListPage />} />
        <Route path="/projects/:projectId" element={<ProjectWorkspacePage />} />
        <Route path="/projects/:projectId/features/:featureId" element={<ProjectWorkspacePage />} />
        <Route path="/settings/llm" element={<LlmSettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
