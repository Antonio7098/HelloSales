import { useDashboardData } from "@/features/dashboard-data/model/use-dashboard-data";
import { Badge } from "@/design-system/primitives/Badge";
import { Skeleton } from "@/design-system/primitives/Skeleton";
import { StatusDot } from "@/design-system/primitives/StatusDot";
import { Surface } from "@/design-system/primitives/Surface";
import { Text } from "@/design-system/primitives/Text";
import { PageHeader } from "@/design-system/patterns/PageHeader";
import { Metric, MetricGrid } from "@/design-system/patterns/Metric";

export function DashboardDataSection() {
  const { data, isLoading, error } = useDashboardData();

  return (
    <>
      <PageHeader
        eyebrow="Profile"
        title={
          <>
            Company <em>profile</em>.
          </>
        }
        description="The company profile defines your sales operating context. All analytics derive from this configuration."
        actions={
          <Badge tone={error ? "danger" : isLoading ? "warn" : "success"}>
            <StatusDot tone={error ? "danger" : isLoading ? "warn" : "success"} />
            {error ? "Error" : isLoading ? "Syncing" : "Live"}
          </Badge>
        }
        meta={
          data ? (
            <span>
              profile <span style={{ color: "var(--ink)" }}>{data.profile_id}</span> · served via
              /api/company-profile
            </span>
          ) : null
        }
      />

      <MetricGrid>
        <Metric
          label="Company"
          value={isLoading ? <Skeleton width="8ch" height="2rem" /> : data?.company_name ?? "—"}
          note="Registered organization"
        />
        <Metric
          label="Industry"
          value={isLoading ? <Skeleton width="6ch" height="2rem" /> : data?.industry ?? "—"}
          note="Business sector"
        />
        <Metric
          label="Target customer"
          value={isLoading ? <Skeleton width="10ch" height="2rem" /> : data?.target_customer ?? "—"}
          note="Ideal customer profile"
        />
        <Metric
          label="Sales team size"
          value={isLoading ? <Skeleton width="3ch" height="2rem" /> : data?.sales_team_size ?? "—"}
          note="Number of reps"
        />
      </MetricGrid>

      {error ? (
        <Surface tone="default" padding="tight">
          <Text>Unable to load company profile: {error.message}</Text>
        </Surface>
      ) : data ? (
        <Surface tone="default" padding="tight">
          <div className="stack-md">
            <div>
              <Text variant="bodyMuted">CRM Tool</Text>
              <Text>{data.crm_tool ?? "—"}</Text>
            </div>
            <div>
              <Text variant="bodyMuted">Pricing Model</Text>
              <Text>{data.pricing_model ?? "—"}</Text>
            </div>
            <div>
              <Text variant="bodyMuted">Average Deal Size</Text>
              <Text>{data.average_deal_size ?? "—"}</Text>
            </div>
            <div>
              <Text variant="bodyMuted">Average Sales Cycle</Text>
              <Text>{data.average_sales_cycle ?? "—"}</Text>
            </div>
            <div>
              <Text variant="bodyMuted">Primary Sales Constraint</Text>
              <Text>{data.primary_sales_constraint ?? "—"}</Text>
            </div>
            <div>
              <Text variant="bodyMuted">Quarterly Sales Focus</Text>
              <Text>{data.quarterly_sales_focus ?? "—"}</Text>
            </div>
          </div>
        </Surface>
      ) : isLoading ? (
        <Surface tone="default" padding="tight">
          <div className="stack-md">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="stack-sm">
                <Skeleton width="10ch" height="0.8rem" />
                <Skeleton width="15ch" height="1.5rem" />
              </div>
            ))}
          </div>
        </Surface>
      ) : null}
    </>
  );
}
