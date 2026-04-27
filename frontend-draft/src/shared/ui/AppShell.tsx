/**
 * AppShell — sidebar + content layout for the signed-in app pages only.
 * /Oliviercontribution.
 *
 * Landing + Signup use PublicLayout; Onboarding uses OnboardingLayout.
 * AppShell wraps Dashboard, Salesbook, Pipeline, Sales Log, Moderation, Team —
 * the actual operating-desk surfaces.
 */

import { NavLink, Outlet } from "react-router-dom";
import type { ComponentType, SVGProps } from "react";
import { StatusDot } from "@/design-system/primitives/StatusDot";
import { useCurrentUser } from "@/shared/auth/useCurrentUser";
import {
  IconBook,
  IconDashboard,
  IconLog,
  IconModeration,
  IconOnboarding,
  IconPipeline,
  IconTeam,
} from "@/shared/icons/NavIcons";

type NavItem = {
  to: string;
  label: string;
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
  adminOnly?: boolean;
};

const navItems: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", Icon: IconDashboard },
  { to: "/salesbook", label: "Salesbook", Icon: IconBook },
  { to: "/pipeline", label: "Pipeline", Icon: IconPipeline },
  { to: "/sales-log", label: "Sales log", Icon: IconLog },
  { to: "/onboarding", label: "Onboarding", Icon: IconOnboarding },
  { to: "/moderation", label: "Moderation", Icon: IconModeration, adminOnly: true },
  { to: "/team", label: "Team", Icon: IconTeam, adminOnly: true },
];

export function AppShell() {
  const { user, signOut } = useCurrentUser();
  const role = user?.role ?? "guest";
  const isAdmin = role === "admin";
  const visibleNav = navItems.filter((item) => !item.adminOnly || isAdmin);

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <NavLink to="/dashboard" className="app-brand" style={{ textDecoration: "none" }}>
          <img src="/hello-sales-icon.png" alt="" className="app-brand-icon" />
          <span>
            Hello<em>Sales</em>
          </span>
        </NavLink>

        <nav className="app-nav" aria-label="Primary">
          {visibleNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? "nav-link is-active" : "nav-link")}
            >
              <item.Icon />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="app-sidebar-footer">
          {user ? (
            <>
              <div className="app-user">
                <div className="app-user-name">{user.name}</div>
                <div className="app-user-meta">
                  {user.companyName} · <span className="app-user-role">{role}</span>
                </div>
              </div>
              <div className="row row--gap-xs">
                <StatusDot tone="success" pulse />
                <span className="text-mono text-body-muted" style={{ fontSize: 11 }}>
                  Demo · no auth
                </span>
              </div>
              <button type="button" onClick={signOut} className="app-signout">
                Sign out
              </button>
            </>
          ) : null}
        </div>
      </aside>
      <main className="app-content">
        <Outlet />
      </main>
    </div>
  );
}
