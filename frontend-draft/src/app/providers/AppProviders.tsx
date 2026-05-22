import type { PropsWithChildren } from "react";
import { BrowserRouter } from "react-router-dom";
import { AppDataProviderRoot } from "@/shared/data/context";

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <AppDataProviderRoot>
      <BrowserRouter>{children}</BrowserRouter>
    </AppDataProviderRoot>
  );
}
