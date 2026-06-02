/**
 * SalesbookPage — the searchable book viewer. /Oliviercontribution.
 *
 * Renders the 114 onboarding questions in book-aesthetic form (Lora serif,
 * paper bg, chapter rules) under .theme-salesbook. Fetches data in order of
 * preference:
 *   1) Backend exhaustive view (live answers) if API reachable
 *   2) Local registry JSON (shape only, placeholders for answers) — always
 *      works offline, no backend required
 *
 * Search bar fuzzy-filters across question text + section + answer. Empty
 * filter → grouped by phase + section as a traditional table of contents.
 */

import { useEffect, useMemo, useState } from "react";
import { useCurrentUser } from "@/shared/auth/useCurrentUser";
import { getSalesbookApi } from "@/features/salesbook";
import type {
  RegistryQuestion,
  SalesbookExhaustiveView,
} from "@/entities/salesbook/types";

type DisplayEntry = {
  phase: number;
  section: string;
  question_key: string;
  question_text: string;
  answer: string | null;
  answer_type: string | null;
};

function normalize(s: string): string {
  return s.toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "");
}

/**
 * Coalesce sections that are really sub-fields of a parent concept.
 * The spreadsheet currently lists each Product field as its own "section"
 * (Product ID, Product Name, ..., 24 of them). We collapse those into a
 * single "Products" section so the book renders 22 logical sections, not 46.
 */
const PRODUCT_FIELD_SECTIONS = new Set([
  "Product ID", "Product Name", "Product Status", "Product Category",
  "Product Description", "Target Customer", "Primary Use Case",
  "Pricing Model", "List Price", "Billing Frequency", "Avg Selling Price",
  "Discount Range", "Cost to Deliver", "Gross Margin", "Sales Complexity",
  "Product Sales Cycle", "Deal Size", "Most Sold Product",
  "Executive Priority", "Strategic Role", "Upsell Potential",
  "Replacement Alternative", "Revenue Contribution", "Internal Notes",
]);

function coalesceSection(phase: number, section: string): string {
  if (phase === 1 && PRODUCT_FIELD_SECTIONS.has(section)) return "Products";
  return section;
}

export function SalesbookPage() {
  const { user } = useCurrentUser();
  const [registry, setRegistry] = useState<Record<string, RegistryQuestion> | null>(null);
  const [exhaustive, setExhaustive] = useState<SalesbookExhaustiveView | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);

  // Pull data. Try the live exhaustive view first (if backend is reachable);
  // always fall back to the static registry so the page works offline.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const api = getSalesbookApi();

      // Static registry (always loads — committed to public/)
      const reg = await api.getOnboardingRegistry().catch(() => null);
      if (!cancelled && reg) setRegistry(reg);

      // Live answers (best-effort; silently skips if no user or no backend)
      if (user?.profileId) {
        const live = await api.getExhaustiveView(user.profileId).catch(() => null);
        if (!cancelled && live) setExhaustive(live);
      }

      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [user?.profileId]);

  // Compose the unified display list
  const allEntries: DisplayEntry[] = useMemo(() => {
    if (!registry) return [];
    const answerByKey = new Map<string, string>();
    if (exhaustive?.onboarding) {
      for (const a of exhaustive.onboarding) {
        if (a.response_value) answerByKey.set(a.question_key, a.response_value);
      }
    }
    return Object.values(registry)
      .map((q) => ({
        phase: q.phase,
        section: coalesceSection(q.phase, q.section ?? "—"),
        question_key: q.key,
        question_text: q.question ?? "",
        answer: answerByKey.get(q.key) ?? null,
        answer_type: q.answer_type ?? null,
      }))
      .sort((a, b) => a.phase - b.phase);
  }, [registry, exhaustive]);

  // Filter
  const filtered = useMemo(() => {
    const q = normalize(query.trim());
    if (!q) return allEntries;
    return allEntries.filter((e) => {
      const hay = [e.section, e.question_text, e.answer ?? ""].map(normalize).join(" ");
      return hay.includes(q);
    });
  }, [allEntries, query]);

  // Group filtered by phase → section
  const grouped = useMemo(() => {
    const byPhase = new Map<number, Map<string, DisplayEntry[]>>();
    for (const e of filtered) {
      if (!byPhase.has(e.phase)) byPhase.set(e.phase, new Map());
      const sectionMap = byPhase.get(e.phase)!;
      if (!sectionMap.has(e.section)) sectionMap.set(e.section, []);
      sectionMap.get(e.section)!.push(e);
    }
    return byPhase;
  }, [filtered]);

  const PHASE_TITLES: Record<number, string> = {
    1: "Phase 1 · Company Onboarding",
    2: "Phase 2 · Sales Book",
    3: "Phase 3 · VP Conversion Intelligence",
  };

  const totalCount = allEntries.length;
  const filteredCount = filtered.length;
  const answeredCount = allEntries.filter((e) => e.answer).length;

  // Build a flat list of all sections for the table of contents (jump links).
  const tableOfContents = useMemo(() => {
    const all = new Map<number, Map<string, number>>();
    for (const e of allEntries) {
      if (!all.has(e.phase)) all.set(e.phase, new Map());
      const m = all.get(e.phase)!;
      m.set(e.section, (m.get(e.section) ?? 0) + 1);
    }
    const out: Array<{ phase: number; section: string; count: number; anchor: string }> = [];
    for (const [phase, sections] of all) {
      for (const [section, count] of sections) {
        out.push({
          phase,
          section,
          count,
          anchor: `phase-${phase}-${section.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`,
        });
      }
    }
    return out;
  }, [allEntries]);

  function sectionAnchor(phase: number, section: string): string {
    return `phase-${phase}-${section.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  }

  if (loading) {
    return (
      <div className="theme-salesbook salesbook-page">
        <div className="salesbook-loading">Opening the book…</div>
      </div>
    );
  }

  return (
    <div className="theme-salesbook salesbook-page">
      <header className="salesbook-header">
        <div className="salesbook-eyebrow">The salesbook</div>
        <h1 className="salesbook-title">
          {user?.companyName ? `${user.companyName}'s` : "Your"} salesbook
        </h1>
        <p className="salesbook-sub">
          Every signal your team has captured — onboarding answers, deals,
          activity — organised like a book. Search across everything below.
        </p>

        <div className="salesbook-stats">
          <span><strong>{answeredCount}</strong> / {totalCount} answered</span>
          {query ? <span>· <strong>{filteredCount}</strong> match "{query}"</span> : null}
          {exhaustive?.pipeline?.length ? (
            <span>· <strong>{exhaustive.pipeline.length}</strong> deals</span>
          ) : null}
          {exhaustive?.engagement?.length ? (
            <span>· <strong>{exhaustive.engagement.length}</strong> activities</span>
          ) : null}
        </div>

        <div className="salesbook-search">
          <input
            type="search"
            className="salesbook-search-input"
            placeholder="Search the salesbook…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
        </div>

        <nav className="salesbook-toc" aria-label="Table of contents">
          <div className="salesbook-toc-label">
            {tableOfContents.length} sections · jump to:
          </div>
          <div className="salesbook-toc-chips">
            {tableOfContents.map((item) => (
              <a key={item.anchor} href={`#${item.anchor}`} className="salesbook-toc-chip">
                <span className="salesbook-toc-phase">P{item.phase}</span>
                {item.section}
                <span className="salesbook-toc-count">{item.count}</span>
              </a>
            ))}
          </div>
        </nav>
      </header>

      <main className="salesbook-body">
        {Array.from(grouped.entries()).map(([phase, sections]) => (
          <section key={phase} className="salesbook-phase">
            <div className="salesbook-chapter">{PHASE_TITLES[phase] ?? `Phase ${phase}`}</div>

            {Array.from(sections.entries()).map(([sectionName, entries]) => (
              <div
                key={sectionName}
                id={sectionAnchor(phase, sectionName)}
                className="salesbook-section"
              >
                <hr className="salesbook-section-rule" />
                <h2 className="salesbook-section-title">
                  {sectionName}
                  <span className="salesbook-section-count">{entries.length}</span>
                </h2>
                <dl className="salesbook-entries">
                  {entries.map((e) => (
                    <div key={e.question_key} className="salesbook-entry">
                      <dt className="salesbook-question">{e.question_text}</dt>
                      <dd className="salesbook-answer">
                        {e.answer ? (
                          highlight(e.answer, query)
                        ) : (
                          <span className="salesbook-empty">— not yet captured</span>
                        )}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            ))}
          </section>
        ))}

        {filtered.length === 0 ? (
          <div className="salesbook-empty-state">
            <em>No entries match "{query}".</em>
          </div>
        ) : null}
      </main>
    </div>
  );
}

function highlight(text: string, query: string): React.ReactNode {
  const q = query.trim();
  if (!q) return text;
  const idx = normalize(text).indexOf(normalize(q));
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="salesbook-mark">{text.slice(idx, idx + q.length)}</mark>
      {text.slice(idx + q.length)}
    </>
  );
}
