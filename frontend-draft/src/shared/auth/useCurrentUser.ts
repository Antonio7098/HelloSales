/**
 * Demo-mode user/workspace state. /Oliviercontribution.
 *
 * For the Vercel demo there's no real auth — we store the signed-up user in
 * localStorage. First visit redirects to /signup. After signup, the user object
 * lives at LS_KEY and drives role-based UI throughout the app.
 *
 * In production (FastAPI mode) this would be replaced by a real session hook
 * that reads from the WorkOS-backed /api/auth/me endpoint. The shape of
 * `CurrentUser` matches the eventual server-side identity contract.
 */

import { useCallback, useEffect, useState } from "react";

export type UserRole = "admin" | "rep";

export type CurrentUser = {
  profileId: string;
  email: string;
  name: string;
  companyName: string;
  role: UserRole;
  signedUpAt: string;
};

const LS_KEY = "hs:user";

function load(): CurrentUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(LS_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as CurrentUser;
  } catch {
    return null;
  }
}

function save(user: CurrentUser | null): void {
  if (typeof window === "undefined") return;
  if (user === null) {
    window.localStorage.removeItem(LS_KEY);
  } else {
    window.localStorage.setItem(LS_KEY, JSON.stringify(user));
  }
  window.dispatchEvent(new CustomEvent("hs:user-changed"));
}

export function useCurrentUser() {
  const [user, setUser] = useState<CurrentUser | null>(() => load());

  useEffect(() => {
    function refresh() {
      setUser(load());
    }
    window.addEventListener("hs:user-changed", refresh);
    window.addEventListener("storage", refresh);
    return () => {
      window.removeEventListener("hs:user-changed", refresh);
      window.removeEventListener("storage", refresh);
    };
  }, []);

  const signIn = useCallback((next: CurrentUser) => {
    save(next);
    setUser(next);
  }, []);

  const signOut = useCallback(() => {
    save(null);
    setUser(null);
  }, []);

  return { user, signIn, signOut };
}
