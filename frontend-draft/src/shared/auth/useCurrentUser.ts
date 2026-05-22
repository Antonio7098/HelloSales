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
import type { CurrentUser, UserRole } from "@/shared/auth/types";
import { useAppData } from "@/shared/data/context";

export type { CurrentUser, UserRole };

export function useCurrentUser() {
  const provider = useAppData();
  const [user, setUser] = useState<CurrentUser | null>(() => provider.getCurrentUser());

  useEffect(() => {
    setUser(provider.getCurrentUser());
    return provider.subscribeCurrentUser(() => {
      setUser(provider.getCurrentUser());
    });
  }, [provider]);

  const signIn = useCallback((next: CurrentUser) => {
    provider.signIn(next);
    setUser(next);
  }, [provider]);

  const signOut = useCallback(() => {
    provider.signOut();
    setUser(null);
  }, [provider]);

  return { user, signIn, signOut };
}
