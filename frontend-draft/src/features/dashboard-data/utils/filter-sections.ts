import type {
  DashboardDataResponse,
  DashboardDataSection,
} from "@/features/dashboard-data/model/types";

export function filterSections(
  data: DashboardDataResponse,
  rawQuery: string,
): { sections: DashboardDataSection[]; visibleCount: number } {
  const query = rawQuery.trim().toLowerCase();
  if (!query) {
    return { sections: data.sections, visibleCount: data.total_entries };
  }

  const sections = data.sections
    .map((section) => {
      const sectionMatches = section.section_label.toLowerCase().includes(query);
      const entries = section.entries.filter((entry) =>
        [entry.prompt_text, entry.example_answer, entry.answer_type, entry.dataset_key]
          .join(" ")
          .toLowerCase()
          .includes(query),
      );
      if (sectionMatches && entries.length === 0) {
        return { ...section, entries: section.entries };
      }
      return { ...section, entries };
    })
    .filter((section) => section.entries.length > 0);

  const visibleCount = sections.reduce((sum, section) => sum + section.entries.length, 0);
  return { sections, visibleCount };
}
