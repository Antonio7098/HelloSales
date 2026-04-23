import { Badge } from "@/design-system/primitives/Badge";
import { Surface } from "@/design-system/primitives/Surface";
import { EntryRow } from "@/features/dashboard-data/components/EntryRow";
import type { DashboardDataSection } from "@/features/dashboard-data/model/types";

type SectionGroupProps = {
  section: DashboardDataSection;
};

export function SectionGroup({ section }: SectionGroupProps) {
  return (
    <Surface tone="bare" padding="flush" className="dataset-section">
      <header className="dataset-section-header" style={{ padding: "0 1rem" }}>
        <div className="row row--gap-sm row--baseline">
          <h2 className="dataset-section-title">{section.section_label}</h2>
          <Badge tone="outline">{section.dataset_key}</Badge>
        </div>
        <span className="text-mono text-body-muted">
          {section.entries.length} {section.entries.length === 1 ? "entry" : "entries"}
        </span>
      </header>
      <div className="entry-list" style={{ padding: "0 1rem" }}>
        {section.entries.map((entry) => (
          <EntryRow key={entry.entry_id} entry={entry} />
        ))}
      </div>
    </Surface>
  );
}
