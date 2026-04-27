import { Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { AppShell } from "@/shared/ui/AppShell";
import { PublicLayout } from "@/shared/ui/layouts/PublicLayout";
import { OnboardingLayout } from "@/shared/ui/layouts/OnboardingLayout";
import { ChatPage } from "@/pages/chat";
import { DashboardPage } from "@/pages/dashboard";
import { NotFoundPage } from "@/pages/not-found";
import { SignupPage } from "@/pages/signup";
import { OnboardingPage } from "@/pages/onboarding";
import { LandingPage } from "@/pages/landing";
import { useCurrentUser } from "@/shared/auth/useCurrentUser";

function RequireUser({ children }: { children: ReactNode }) {
  const { user } = useCurrentUser();
  if (!user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function RootRedirect() {
  const { user } = useCurrentUser();
  return <Navigate to={user ? "/dashboard" : "/welcome"} replace />;
}

export function AppRouter() {
  return (
    <Routes>
      {/* Public — no sidebar, marketing-style */}
      <Route element={<PublicLayout />}>
        <Route index element={<RootRedirect />} />
        <Route path="welcome" element={<LandingPage />} />
      </Route>

      {/* Signup — owns its full viewport, mono minimal aesthetic */}
      <Route path="signup" element={<SignupPage />} />

      {/* Onboarding — focus mode, minimal chrome, no app sidebar */}
      <Route element={<OnboardingLayout />}>
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
      </Route>

      {/* App — sidebar + content */}
      <Route element={<AppShell />}>
        <Route
          path="dashboard"
          element={
            <RequireUser>
              <DashboardPage />
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
