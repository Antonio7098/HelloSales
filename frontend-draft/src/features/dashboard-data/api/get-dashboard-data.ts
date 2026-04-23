import { requestJson } from "@/shared/api/http-client";
import type { ApiEnvelope, DashboardDataResponse } from "@/features/dashboard-data/model/types";

export async function getDashboardData(): Promise<DashboardDataResponse> {
  const response = await requestJson<ApiEnvelope<DashboardDataResponse>>({
    path: "/dashboard-data/entries",
  });
  return response.data;
}
