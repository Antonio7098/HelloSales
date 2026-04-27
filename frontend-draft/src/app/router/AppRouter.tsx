import { Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { AppShell } from "@/shared/ui/AppShell";
import { ChatPage } from "@/pages/chat";
import { DashboardPage } from "@/pages/dashboard";
import { NotFoundPage } from "@/pages/not-found";
import { SignupPage } from "@/pages/signup";
import { OnboardingPage } from "@/pages/onboarding";
import { useCurrentUser } from "@/shared/auth/useCurrentUser";

function RequireUser({ children }: { children: ReactNode }) {
  const { user } = useCurrentUser();
  if (!user) return <Navigate to="/signup" replace />;
  return <>{children}</>;
}

function RootRedirect() {
  const { user } = useCurrentUser();
  return <Navigate to={user ? "/dashboard" : "/signup"} replace />;
}

export function AppRouter() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<RootRedirect />} />
        <Route path="signup" element={<SignupPage />} />
        <Route
          path="dashboard"
          element={
            <RequireUser>
              <DashboardPage />
            </RequireUser>
          }
        />
        <Route
          path="onboarding"
          element={
            <RequireUser>
              <OnboardingPage />
            </RequireUser>
          }
        />
        <Route
          path="onboarding/:sectionIndex"
          element={
            <RequireUser>
              <OnboardingPage />
            </RequireUser>
          }
        />
        <Route path="chat" element={<ChatPage />} />
        <Route path="404" element={<NotFoundPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  );
}
