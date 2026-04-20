import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/shared/ui/AppShell";
import { HomePage } from "@/pages/home";
import { PipelinePage } from "@/pages/pipeline";
import { NotFoundPage } from "@/pages/not-found";

export function AppRouter() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<HomePage />} />
        <Route path="pipeline" element={<PipelinePage />} />
        <Route path="404" element={<NotFoundPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  );
}
