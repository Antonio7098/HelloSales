import { useEffect, useState } from "react";
import { getDashboardData } from "@/features/dashboard-data/api/get-dashboard-data";
import type { DashboardDataResponse } from "@/features/dashboard-data/model/types";

type DashboardDataState = {
  data: DashboardDataResponse | null;
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

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setState((current) => ({ ...current, isLoading: true, error: null }));
      try {
        const data = await getDashboardData();
        if (cancelled) {
          return;
        }
        setState({
          data,
          isLoading: false,
          error: null,
        });
      } catch (error) {
        if (cancelled) {
          return;
        }
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
  }, []);

  return state;
}
