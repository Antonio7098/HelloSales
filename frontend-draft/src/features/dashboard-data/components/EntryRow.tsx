import { Badge } from "@/design-system/primitives/Badge";
import type { DashboardDataEntry } from "@/features/dashboard-data/model/types";
import {
  answerTypeTone,
  formatAnswerType,
} from "@/features/dashboard-data/utils/format-answer-type";

type EntryRowProps = {
  entry: DashboardDataEntry;
};

export function EntryRow({ entry }: EntryRowProps) {
  return (
    <article className="entry-row">
      <div className="entry-index">#{String(entry.sequence_no).padStart(2, "0")}</div>
      <div className="entry-prompt">{entry.prompt_text}</div>
      <div className="entry-example" title={entry.example_answer}>
        {entry.example_answer || <span className="text-body-muted">—</span>}
      </div>
      <div className="entry-meta">
        <Badge tone={answerTypeTone(entry.answer_type)}>{formatAnswerType(entry.answer_type)}</Badge>
      </div>
    </article>
  );
}
