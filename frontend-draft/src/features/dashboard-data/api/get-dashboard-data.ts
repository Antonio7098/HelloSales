import { requestJson } from "@/shared/api/http-client";
import type { ApiEnvelope, CompanyProfileResponse } from "@/features/dashboard-data/model/types";

export async function getDashboardData(): Promise<CompanyProfileResponse> {
  const response = await requestJson<ApiEnvelope<CompanyProfileResponse>>({
    path: "/company-profile",
  });
  return response.data;
}
