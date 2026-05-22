/**
 * OnboardingLayout — strict focus mode. /Oliviercontribution.
 *
 * No app sidebar. Top bar carries only: brand mark, phase progress dots,
 * and a small "exit to dashboard" link. The whole job of the layout is to
 * stay out of the way of the question being answered.
 */

import { Link, Outlet } from "react-router-dom";
import { IconClose } from "@/shared/icons/NavIcons";
import { useCurrentUser } from "@/shared/auth/useCurrentUser";

export function OnboardingLayout() {
  const { user } = useCurrentUser();
  return (
    <div className="onboarding-layout">
      <header className="onboarding-header">
        <Link to="/" className="onboarding-brand">
          <img src="/hello-sales-icon.png" alt="Hello Sales logo" className="onboarding-brand-icon" />
          <span>
            Hello<em>Sales</em>
          </span>
        </Link>
        {user ? (
          <Link to="/dashboard" className="onboarding-exit" aria-label="Exit to dashboard">
            <IconClose />
          </Link>
        ) : null}
      </header>
      <main className="onboarding-main">
        <Outlet />
      </main>
    </div>
  );
}
