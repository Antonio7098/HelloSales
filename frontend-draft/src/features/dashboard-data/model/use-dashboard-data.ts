import { useEffect, useState } from "react";
import { useAppData } from "@/shared/data/context";
import type { CompanyProfileResponse } from "@/features/dashboard-data/model/types";

type DashboardDataState = {
  data: CompanyProfileResponse | null;
  isLoading: boolean;
  error: Error | null;
};

const initialState: DashboardDataState = {
  data: null,
  isLoading: true,
  error: null,
};

export function useDashboardData() {
  const [state, setState] = useState<DashboardDataState>(initialState);
  const provider = useAppData();

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setState((current) => ({ ...current, isLoading: true, error: null }));
      try {
        const data = await provider.getDashboardData();
        if (cancelled) return;
        setState({ data, isLoading: false, error: null });
      } catch (error) {
        if (cancelled) return;
        setState({
          data: null,
          isLoading: false,
          error: error instanceof Error ? error : new Error("Failed to load dashboard data"),
        });
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [provider]);

  return state;
}