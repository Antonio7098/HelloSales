/**
 * PublicLayout — used by Landing + Signup. /Oliviercontribution.
 *
 * No sidebar. Single full-bleed canvas so the page itself sets the tone.
 * Top brand bar is minimal so the focus stays on whatever the page is doing.
 */

import { Outlet, Link } from "react-router-dom";

export function PublicLayout() {
  return (
    <div className="public-layout">
      <header className="public-header">
        <Link to="/" className="public-brand">
          <img src="/hello-sales-icon.png" alt="" className="public-brand-icon" />
          <span>
            Hello<em>Sales</em>
          </span>
        </Link>
      </header>
      <main className="public-main">
        <Outlet />
      </main>
    </div>
  );
}
