import { NavLink, Outlet } from "react-router-dom";
import { StatusDot } from "@/design-system/primitives/StatusDot";
import { Text } from "@/design-system/primitives/Text";
import { useCurrentUser } from "@/shared/auth/useCurrentUser";

type NavItem = {
  to: string;
  label: string;
  shortcut?: string;
  description: string;
  adminOnly?: boolean;
};

const navItems: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", shortcut: "D", description: "Your overview" },
  { to: "/onboarding", label: "Onboarding", shortcut: "O", description: "Build your sales context" },
  { to: "/salesbook", label: "Salesbook", shortcut: "B", description: "Searchable knowledge book" },
  { to: "/pipeline", label: "Pipeline", shortcut: "P", description: "Deal flow" },
  { to: "/sales-log", label: "Sales Log", shortcut: "L", description: "Activity stream" },
  { to: "/moderation", label: "Moderation", shortcut: "M", description: "Approve rep contributions", adminOnly: true },
  { to: "/team", label: "Team", shortcut: "T", description: "Roster & roles", adminOnly: true },
];

export function AppShell() {
  const { user, signOut } = useCurrentUser();
  const role = user?.role ?? "guest";
  const isAdmin = role === "admin";
  const visibleNav = navItems.filter((item) => !item.adminOnly || isAdmin);

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="stack-2xs">
          <NavLink
            to={user ? "/dashboard" : "/signup"}
            className="app-brand"
            style={{ textDecoration: "none" }}
          >
            <img src="/hello-sales-icon.png" alt="" className="app-brand-icon" />
            <span>
              Hello<em>Sales</em>
            </span>
          </NavLink>
          <Text variant="mono" className="text-body-muted">
            {user ? `${user.companyName} · ${role}` : "Sales intelligence platform"}
          </Text>
        </div>

        {user ? (
          <div className="stack-2xs">
            <div className="app-nav-label">Workspace</div>
            <nav className="app-nav" aria-label="Primary">
              {visibleNav.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) => (isActive ? "nav-link is-active" : "nav-link")}
                >
                  <span>{item.label}</span>
                  {item.shortcut ? <kbd>{item.shortcut}</kbd> : null}
                </NavLink>
              ))}
            </nav>
          </div>
        ) : null}

        <div className="app-sidebar-footer">
          <div className="row row--gap-xs">
            <StatusDot tone="success" pulse />
            <Text variant="mono" className="text-body-muted">
              {user ? user.email : "Demo · no auth"}
            </Text>
          </div>
          {user ? (
            <button
              type="button"
              onClick={signOut}
              className="nav-link"
              style={{ textAlign: "left", width: "100%" }}
            >
              Sign out
            </button>
          ) : null}
          <Text variant="mono" className="text-body-muted">
            v0.1 · /Oliviercontribution
          </Text>
        </div>
      </aside>
      <main className="app-content">
        <Outlet />
      </main>
    </div>
  );
}
