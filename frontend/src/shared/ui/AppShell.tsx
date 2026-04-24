import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/app/providers/auth-context";
import { Text } from "@/design-system/primitives/Text";

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/pipeline", label: "Pipeline", end: false },
];

export function AppShell() {
  const auth = useAuth();

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="stack-sm">
          <Text as="div" variant="sectionTitle">
            HelloSales
          </Text>
          <div className="stack-xs">
            <Text variant="bodyStrong">{auth.session?.email ?? auth.session?.user_id}</Text>
            <Text variant="bodyMuted">{auth.session?.org_id ?? "No organization selected"}</Text>
          </div>
        </div>
        <nav className="stack-sm">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => (isActive ? "nav-link is-active" : "nav-link")}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button type="button" className="action-button action-button-secondary" onClick={() => void auth.logout()}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="app-content">
        <Outlet />
      </main>
    </div>
  );
}
