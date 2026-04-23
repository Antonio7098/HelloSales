import { useMemo, useState } from "react";
import { Badge } from "@/design-system/primitives/Badge";
import { Skeleton } from "@/design-system/primitives/Skeleton";
import { StatusDot } from "@/design-system/primitives/StatusDot";
import { Surface } from "@/design-system/primitives/Surface";
import { Text } from "@/design-system/primitives/Text";
import { EmptyState } from "@/design-system/patterns/EmptyState";
import { Metric, MetricGrid } from "@/design-system/patterns/Metric";
import { PageHeader } from "@/design-system/patterns/PageHeader";
import { DatasetToolbar } from "@/features/dashboard-data/components/DatasetToolbar";
import { SectionGroup } from "@/features/dashboard-data/components/SectionGroup";
import { useDashboardData } from "@/features/dashboard-data/model/use-dashboard-data";
import { filterSections } from "@/features/dashboard-data/utils/filter-sections";

export function DashboardDataSection() {
  const { data, isLoading, error } = useDashboardData();
  const [query, setQuery] = useState("");

  const filtered = useMemo(
    () => (data ? filterSections(data, query) : null),
    [data, query],
  );

  const totalEntries = data?.total_entries ?? 0;
  const sectionCount = data?.sections.length ?? 0;
  const answerTypes = useMemo(() => {
    if (!data) return 0;
    const set = new Set<string>();
    for (const section of data.sections) {
      for (const entry of section.entries) {
        set.add(entry.answer_type);
      }
    }
    return set.size;
  }, [data]);

  return (
    <>
      <PageHeader
        eyebrow="Governed substrate"
        title={
          <>
            The sales operating <em>substrate</em>.
          </>
        }
        description="Every prompt below is read and written only through the approved catalog. The analyst consults this table; humans edit it."
        actions={
          <Badge tone={error ? "danger" : isLoading ? "warn" : "success"}>
            <StatusDot tone={error ? "danger" : isLoading ? "warn" : "success"} />
            {error ? "Error" : isLoading ? "Syncing" : "Live"}
          </Badge>
        }
        meta={
          data ? (
            <span>
              dataset <span style={{ color: "var(--ink)" }}>hello_sales_mvp</span> · served via
              /api/dashboard-data/entries
            </span>
          ) : null
        }
      />

      <MetricGrid>
        <Metric
          label="Governed entries"
          value={isLoading ? <Skeleton width="3ch" height="2rem" /> : totalEntries}
          note="Rows exposed to the analyst"
        />
        <Metric
          label="Sections"
          value={isLoading ? <Skeleton width="2ch" height="2rem" /> : sectionCount}
          note="Logical groupings"
        />
        <Metric
          label="Answer shapes"
          value={isLoading ? <Skeleton width="2ch" height="2rem" /> : answerTypes}
          note="Distinct answer types"
        />
        <Metric
          label="Access path"
          value={<span style={{ fontSize: "1rem", letterSpacing: 0 }}>SQL · read-only</span>}
          note="Governed analytics catalog"
        />
      </MetricGrid>

      <Surface tone="bare" padding="tight">
        <DatasetToolbar
          query={query}
          onQueryChange={setQuery}
          sectionCount={filtered?.sections.length ?? 0}
          visibleCount={filtered?.visibleCount ?? 0}
          totalCount={totalEntries}
        />
      </Surface>

      {error ? (
        <EmptyState
          eyebrow="Unable to load"
          title="The substrate could not be reached."
          description={error.message}
        />
      ) : isLoading ? (
        <LoadingSections />
      ) : !filtered || filtered.sections.length === 0 ? (
        <EmptyState
          eyebrow="No results"
          title="Nothing matches that search."
          description="Try a different keyword, or clear the search to see every governed entry."
        />
      ) : (
        <div className="stack-md">
          {filtered.sections.map((section) => (
            <SectionGroup key={section.dataset_key + section.section_label} section={section} />
          ))}
        </div>
      )}
    </>
  );
}

function LoadingSections() {
  return (
    <div className="stack-md">
      {[0, 1].map((i) => (
        <Surface key={i} tone="bare" padding="tight">
          <div className="stack-sm">
            <Skeleton width="14rem" height="1.3rem" />
            {[0, 1, 2, 3].map((k) => (
              <div key={k} className="row row--gap-md" style={{ alignItems: "flex-start" }}>
                <Skeleton width="2rem" height="1rem" />
                <Skeleton height="1rem" />
                <Skeleton width="5rem" height="1rem" />
              </div>
            ))}
          </div>
        </Surface>
      ))}
      <span className="sr-only" aria-live="polite">
        <Text variant="bodyMuted">Loading governed entries…</Text>
      </span>
    </div>
  );
}
