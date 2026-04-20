import { NavLink, Outlet } from "react-router-dom";
import { Text } from "@/design-system/primitives/Text";

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/pipeline", label: "Pipeline", end: false },
];

export function AppShell() {
  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <Text as="div" variant="sectionTitle">
          HelloSales
        </Text>
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
      </aside>
      <main className="app-content">
        <Outlet />
      </main>
    </div>
  );
}
