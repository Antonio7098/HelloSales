import { Badge } from "@/design-system/primitives/Badge";
import { Input } from "@/design-system/primitives/Field";

type DatasetToolbarProps = {
  query: string;
  onQueryChange: (next: string) => void;
  sectionCount: number;
  visibleCount: number;
  totalCount: number;
};

export function DatasetToolbar({
  query,
  onQueryChange,
  sectionCount,
  visibleCount,
  totalCount,
}: DatasetToolbarProps) {
  return (
    <div className="dataset-toolbar">
      <Input
        type="search"
        value={query}
        placeholder="Search prompts, sections, examples…"
        onChange={(event) => onQueryChange(event.target.value)}
        aria-label="Search governed entries"
      />
      <Badge tone="outline">
        {visibleCount} / {totalCount} entries
      </Badge>
      <Badge tone="outline">
        {sectionCount} {sectionCount === 1 ? "section" : "sections"}
      </Badge>
    </div>
  );
}
