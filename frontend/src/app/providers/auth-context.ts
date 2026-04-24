import { createContext, useContext } from "react";

export type AuthSession = {
  provider_name: string;
  actor_id: string;
  user_id: string;
  session_id: string | null;
  org_id: string | null;
  email: string | null;
  roles: string[];
  permissions: string[];
  impersonator_email: string | null;
};

export type AuthStatus = "loading" | "authenticated" | "anonymous";

export type AuthContextValue = {
  status: AuthStatus;
  session: AuthSession | null;
  refresh: () => Promise<void>;
  login: (returnPath?: string) => void;
  logout: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth() {
  const value = useContext(AuthContext);
  if (value === null) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return value;
}
