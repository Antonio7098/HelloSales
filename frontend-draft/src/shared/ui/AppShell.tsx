import { NavLink, Outlet } from "react-router-dom";
import { StatusDot } from "@/design-system/primitives/StatusDot";
import { Text } from "@/design-system/primitives/Text";

type NavItem = {
  to: string;
  label: string;
  shortcut?: string;
  description: string;
};

const navItems: NavItem[] = [
  { to: "/dashboard", label: "Substrate", shortcut: "D", description: "Governed dashboard data" },
  { to: "/chat", label: "Analyst", shortcut: "C", description: "Agent with SQL tool" },
];

export function AppShell() {
  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="stack-2xs">
          <div className="app-brand">
            <span className="app-brand-mark" aria-hidden="true">
              hs
            </span>
            <span>
              Hello<em>Sales</em>
            </span>
          </div>
          <Text variant="mono" className="text-body-muted">
            Sales Operating Desk
          </Text>
        </div>

        <div className="stack-2xs">
          <div className="app-nav-label">Workspace</div>
          <nav className="app-nav" aria-label="Primary">
            {navItems.map((item) => (
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

        <div className="app-sidebar-footer">
          <div className="row row--gap-xs">
            <StatusDot tone="success" pulse />
            <Text variant="mono" className="text-body-muted">
              Runtime online
            </Text>
          </div>
          <Text variant="mono" className="text-body-muted">
            v0.1 · governed catalog
          </Text>
        </div>
      </aside>
      <main className="app-content">
        <Outlet />
      </main>
    </div>
  );
}
