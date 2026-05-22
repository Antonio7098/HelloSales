/**
 * Polymorphic question input. /Oliviercontribution.
 *
 * Reads the registry entry's `answer_type` and dispatches to the right control.
 * Calls onChange with a string (the canonical wire shape — backend stores
 * everything as text). Multi-value answers (multi_choice, editable_bullets) are
 * JSON-stringified so the wire shape stays simple.
 */

import { Field, Input, Textarea } from "@/design-system";
import type { RegistryQuestion } from "@/entities/salesbook/types";

type Props = {
  question: RegistryQuestion;
  value: string;
  onChange: (next: string) => void;
};

function asArray(value: string): string[] {
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? (parsed as string[]) : [String(parsed)];
  } catch {
    return value.split("\n").filter(Boolean);
  }
}

export function QuestionInput({ question, value, onChange }: Props) {
  const t = (question.answer_type ?? "Text").toLowerCase();

  return (
    <Field
      label={
        <span>
          <strong>Q{question.n}.</strong> {question.question}
        </span>
      }
      hint={question.example ? `e.g. ${question.example}` : undefined}
    >
      {({ id }) => renderControl(id, t, value, onChange, question)}
    </Field>
  );
}

function renderControl(
  id: string,
  t: string,
  value: string,
  onChange: (v: string) => void,
  q: RegistryQuestion,
) {
  if (t === "text" || t === "options + text" || t === "options_text") {
    return (
      <Input
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={q.example ?? ""}
      />
    );
  }
  if (t === "numeric" || t === "numeric (%)" || t === "numeric_pct") {
    return (
      <Input
        id={id}
        type="number"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={q.example ?? ""}
      />
    );
  }
  if (t === "numeric scale" || t === "numeric_scale") {
    return (
      <Input
        id={id}
        type="number"
        min={1}
        max={10}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="1–10"
      />
    );
  }
  if (t === "date") {
    return (
      <Input id={id} type="date" value={value} onChange={(e) => onChange(e.target.value)} />
    );
  }
  if (t === "options" || t === "multi-choice" || t === "multi_choice") {
    // No options enum from the spreadsheet → free-text fallback for now.
    // The Apps Script / FastAPI accepts any string.
    return (
      <Input
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={q.example ?? "Pick one (free text for now)"}
      />
    );
  }
  if (
    t === "editable bullets" ||
    t === "editable_bullets" ||
    t === "editable options" ||
    t === "editable_options" ||
    t === "editable ranking" ||
    t === "editable_ranking"
  ) {
    const items = asArray(value);
    return (
      <BulletEditor
              id={id}
              items={items}
              onChange={(arr) => onChange(JSON.stringify(arr))}
              inputId={id}
            />
    );
  }
  if (t === "text upload" || t === "text_upload") {
    return (
      <Textarea
        id={id}
        rows={6}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Paste content here…"
      />
    );
  }
  if (t === "file upload" || t === "file_upload") {
    return (
      <Input
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="(file upload coming soon — paste a URL for now)"
      />
    );
  }
  // Fallback — generic textarea so no question is unrenderable
  return (
    <Textarea
      id={id}
      rows={3}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={q.example ?? ""}
    />
  );
}

function BulletEditor({
  id,
  items,
  onChange,
  inputId,
}: {
  id: string;
  items: string[];
  onChange: (next: string[]) => void;
  inputId?: string;
}) {
  const list = items.length > 0 ? items : [""];
  return (
    <div id={id} className="bullet-editor stack-2xs">
      {list.map((item, idx) => (
        <div key={idx} className="row row--gap-xs">
          <span className="text-body-muted" style={{ width: 18, flexShrink: 0 }}>
            {idx + 1}.
          </span>
          <Input
            id={inputId ? (idx === 0 ? inputId : `${inputId}-${idx}`) : undefined}
            onChange={(e) => {
              const next = [...list];
              next[idx] = e.target.value;
              onChange(next);
            }}
            placeholder={`Item ${idx + 1}`}
          />
          <button
            type="button"
            className="nav-link"
            style={{ padding: "0.25rem 0.6rem" }}
            onClick={() => {
              const next = list.filter((_, i) => i !== idx);
              onChange(next.length === 0 ? [] : next);
            }}
            aria-label="Remove"
          >
            ×
          </button>
        </div>
      ))}
      <button
        type="button"
        className="nav-link"
        style={{ alignSelf: "flex-start", padding: "0.25rem 0.6rem" }}
        onClick={() => onChange([...list, ""])}
      >
        + Add another
      </button>
    </div>
  );
}
