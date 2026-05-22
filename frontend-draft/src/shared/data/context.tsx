import { createContext, type PropsWithChildren, useContext } from "react";
import { getAppDataProvider } from "@/shared/data/get-provider";
import type { AppDataProvider } from "@/shared/data/provider";

const AppDataProviderContext = createContext<AppDataProvider | null>(null);

export function AppDataProviderRoot({ children }: PropsWithChildren) {
  return <AppDataProviderContext.Provider value={getAppDataProvider()}>{children}</AppDataProviderContext.Provider>;
}

export function useAppData() {
  const provider = useContext(AppDataProviderContext);
  if (!provider) {
    throw new Error("useAppData must be used inside AppDataProviderRoot");
  }
  return provider;
}
