export type ApiEnvelope<T> = {
  ok: true;
  data: T;
};

export type CompanyProfileResponse = {
  profile_id: string;
  company_name: string;
  industry: string | null;
  target_customer: string | null;
  pricing_model: string | null;
  sales_team_size: number | null;
  crm_tool: string | null;
  average_deal_size: string | null;
  average_sales_cycle: string | null;
  primary_sales_constraint: string | null;
  quarterly_sales_focus: string | null;
  created_at: string;
  updated_at: string;
};
