import type { AppDataProvider } from "@/shared/data/provider";
import { mockDataProvider } from "@/shared/data/mock-data-provider";
import { realDataProvider } from "@/shared/data/real-data-provider";

let provider: AppDataProvider | null = null;

export function getAppDataProvider(): AppDataProvider {
  if (provider) return provider;
  provider = import.meta.env.VITE_DATA_PROVIDER === "mock" ? mockDataProvider : realDataProvider;
  return provider;
}
