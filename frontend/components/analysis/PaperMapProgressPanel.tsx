"use client";

import { BookOpen, RefreshCw, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { DocumentSection, PaperMap } from "@/lib/types";

function pdfPageFromLabel(label: string | null): number | null {
  if (!label) return null;
  const m = label.match(/^PDF page (\d+)$/);
  return m ? parseInt(m[1], 10) : null;
}

export function PaperMapProgressPanel({ documentId, refreshKey = 0 }: { documentId: string; refreshKey?: number }) {
  const [paperMap, setPaperMap] = useState<PaperMap | null>(null);
  const [sections, setSections] = useState<DocumentSection[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const [map, secs] = await Promise.all([
        api.getPaperMap(documentId),
        api.listDocumentSections(documentId).catch(() => [] as DocumentSection[])
      ]);
      setPaperMap(map);
      setSections(secs);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [documentId, refreshKey]);

  useEffect(() => {
    if (!expanded) return;
    function onKeyDown(e: KeyboardEvent) { if (e.key === "Escape") setExpanded(false); }
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    return () => { document.body.style.overflow = prev; window.removeEventListener("keydown", onKeyDown); };
  }, [expanded]);

  if (!paperMap && loading) return null;
  if (!paperMap) return null;

  const analyzedCount = paperMap.analyzed_sections.length;
  const totalSections = paperMap.total_sections || Math.max(analyzedCount, 1);
  const progress = totalSections ? Math.min(100, Math.round((analyzedCount / totalSections) * 100)) : 0;
  const complete = Boolean(totalSections && analyzedCount >= totalSections);

  return (
    <section className="rounded-lg border border-line bg-panel shadow-material">
      <div className="flex items-center gap-3 px-4 py-3">
        <BookOpen size={14} className="shrink-0 text-neutral-400" />
        <span className="min-w-0 flex-1 text-sm font-semibold text-ink">Paper map</span>
        <div className="flex shrink-0 items-center gap-2">
          {!complete ? (
            <>
              <span className="h-1.5 w-20 overflow-hidden rounded-full bg-surface">
                <span className="block h-full rounded-full bg-accent transition-all" style={{ width: `${progress}%` }} />
              </span>
              <span className="min-w-[5rem] text-right text-xs tabular-nums text-neutral-500">
                {analyzedCount} / {totalSections}
              </span>
            </>
          ) : (
            <span className="text-xs font-semibold text-emerald-700">Complete</span>
          )}
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-line bg-surface text-neutral-500 hover:bg-white disabled:opacity-40"
            title="Refresh"
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          </button>
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface px-2.5 py-1.5 text-xs font-semibold text-ink hover:bg-white"
          >
            Open map
          </button>
        </div>
      </div>
      {expanded ? (
        <PaperMapModal
          paperMap={paperMap}
          sections={sections}
          complete={complete}
          onClose={() => setExpanded(false)}
        />
      ) : null}
    </section>
  );
}

// ─── Modal ───────────────────────────────────────────────────────────────────

function PaperMapModal({
  paperMap,
  sections,
  complete,
  onClose,
}: {
  paperMap: PaperMap;
  sections: DocumentSection[];
  complete: boolean;
  onClose: () => void;
}) {
  const [activeTab, setActiveTab] = useState<"overview" | "argument" | "concepts" | "vocabulary">("overview");
  const analyzedSet = new Set(paperMap.analyzed_sections);

  const guide = paperMap.guide ?? {
    title: "Reading guide",
    thesis_so_far: "No overview available yet.",
    coverage_note: "",
    reading_focus: [],
    next_steps: [],
  };
  const synthesis = paperMap.synthesis ?? {
    status: "partial",
    argument_flow: [],
    priority_concepts: paperMap.top_concepts.slice(0, 6),
    priority_terms: paperMap.top_terms.slice(0, 8),
    reusable_expressions: paperMap.top_phrases.slice(0, 6),
    review_plan: [],
  };

  const tabs: { id: typeof activeTab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "argument", label: "Argument" },
    { id: "concepts", label: "Concepts" },
    { id: "vocabulary", label: "Vocabulary" },
  ];

  return (
    <div className="fixed inset-0 z-50 bg-ink/30 px-4 py-6 backdrop-blur-sm" role="dialog" aria-modal="true">
      <div className="mx-auto flex h-[min(90vh,1000px)] w-[min(1100px,96vw)] flex-col overflow-hidden rounded-xl border border-line bg-panel shadow-material">
        {/* Header */}
        <div className="flex items-center justify-between gap-4 border-b border-line px-6 py-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold text-neutral-500">
              Paper map · {complete ? "complete" : `${paperMap.analyzed_sections.length} / ${paperMap.total_sections ?? "?"} sections`}
            </p>
            <h2 className="mt-0.5 text-lg font-semibold text-ink">
              {complete ? "Whole-paper guide" : "Building as sections finish"}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-line text-neutral-600 hover:bg-surface"
            aria-label="Close"
          >
            <X size={17} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-line bg-panel">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`px-5 py-3 text-sm font-semibold transition-colors ${
                activeTab === tab.id
                  ? "border-b-2 border-accent text-accent"
                  : "text-neutral-500 hover:text-ink"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="min-h-0 flex-1 overflow-y-auto bg-surface p-6">
          {activeTab === "overview" && (
            <OverviewTab
              paperMap={paperMap}
              sections={sections}
              analyzedSet={analyzedSet}
              guide={guide}
              complete={complete}
            />
          )}
          {activeTab === "argument" && (
            <ArgumentTab synthesis={synthesis} complete={complete} />
          )}
          {activeTab === "concepts" && (
            <ConceptsTab paperMap={paperMap} />
          )}
          {activeTab === "vocabulary" && (
            <VocabularyTab synthesis={synthesis} />
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Overview tab ─────────────────────────────────────────────────────────────

function OverviewTab({
  paperMap,
  sections,
  analyzedSet,
  guide,
  complete,
}: {
  paperMap: PaperMap;
  sections: DocumentSection[];
  analyzedSet: Set<number>;
  guide: NonNullable<PaperMap["guide"]>;
  complete: boolean;
}) {
  // Build section→summary lookup
  const summaryBySection = new Map<number, { oneLine: string; academic: string }>();
  for (const s of paperMap.section_summaries) {
    for (const n of s.sections) {
      summaryBySection.set(n, { oneLine: s.text, academic: s.meaning });
    }
  }

  // Group sections by PDF page
  type PageGroup = { page: number | null; label: string; items: DocumentSection[] };
  const groups: PageGroup[] = [];
  if (sections.length) {
    const map = new Map<string, PageGroup>();
    for (const sec of sections) {
      const page = pdfPageFromLabel(sec.source_label);
      const key = page ? `p${page}` : "unknown";
      if (!map.has(key)) {
        const g: PageGroup = { page, label: page ? `Page ${page}` : "Unknown", items: [] };
        map.set(key, g);
        groups.push(g);
      }
      map.get(key)!.items.push(sec);
    }
  }

  const [hoveredSection, setHoveredSection] = useState<number | null>(null);
  const hoveredSummary = hoveredSection !== null ? summaryBySection.get(hoveredSection) : undefined;

  return (
    <div className="space-y-5">
      {/* Thesis / coverage */}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_280px]">
        <div className="rounded-lg border border-line bg-panel p-5">
          <p className="text-xs font-semibold text-neutral-500">Thesis so far</p>
          <p className="mt-2 text-sm leading-7 text-ink">{guide.thesis_so_far}</p>
          {guide.reading_focus.length ? (
            <ul className="mt-4 space-y-2">
              {guide.reading_focus.slice(0, 3).map((item) => (
                <li key={item} className="flex items-start gap-2.5 text-sm leading-6 text-neutral-700">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                  {item}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        <div className="rounded-lg border border-line bg-panel p-5">
          <p className="text-xs font-semibold text-neutral-500">Next steps</p>
          {guide.next_steps.length ? (
            <ul className="mt-3 space-y-2">
              {guide.next_steps.slice(0, 4).map((item) => (
                <li key={item} className="flex items-start gap-2.5 text-sm leading-6 text-neutral-700">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-neutral-300" />
                  {item}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-neutral-400">Analyze more sections.</p>
          )}
        </div>
      </div>

      {/* Section map */}
      <div className="rounded-lg border border-line bg-panel p-5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <p className="text-xs font-semibold text-neutral-500">Section map</p>
          <span className="text-[11px] text-neutral-400">{analyzedSet.size} / {paperMap.total_sections ?? "?"} analyzed</span>
        </div>

        {groups.length ? (
          <div className="space-y-1">
            {groups.map((group) => (
              <div key={group.label}>
                <p className="mb-1 mt-3 text-[10px] font-semibold uppercase tracking-wider text-neutral-400 first:mt-0">{group.label}</p>
                <div className="space-y-0.5">
                  {group.items.map((sec) => {
                    const isAnalyzed = analyzedSet.has(sec.section_number);
                    const summary = summaryBySection.get(sec.section_number);
                    return (
                      <div
                        key={sec.index}
                        onMouseEnter={() => setHoveredSection(sec.section_number)}
                        onMouseLeave={() => setHoveredSection(null)}
                        className={`flex items-center gap-3 rounded-md px-3 py-2 transition-colors ${
                          isAnalyzed ? "bg-blue-50" : "bg-neutral-50 hover:bg-neutral-100"
                        }`}
                      >
                        <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                          isAnalyzed ? "bg-accent text-white" : "bg-neutral-200 text-neutral-500"
                        }`}>{sec.section_number}</span>
                        <span className={`min-w-0 flex-1 truncate text-xs ${isAnalyzed ? "font-medium text-ink" : "text-neutral-500"}`}>
                          {summary?.oneLine ?? sec.title ?? `Section ${sec.section_number}`}
                        </span>
                        {isAnalyzed ? <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" /> : null}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        ) : (
          /* Fallback: no sections prop, compact numbered list */
          <div className="space-y-0.5">
            {Array.from({ length: paperMap.total_sections }, (_, i) => i + 1).map((n) => {
              const isAnalyzed = analyzedSet.has(n);
              const summary = summaryBySection.get(n);
              return (
                <div
                  key={n}
                  onMouseEnter={() => setHoveredSection(n)}
                  onMouseLeave={() => setHoveredSection(null)}
                  className={`flex items-center gap-3 rounded-md px-3 py-2 transition-colors ${
                    isAnalyzed ? "bg-blue-50" : "bg-neutral-50 hover:bg-neutral-100"
                  }`}
                >
                  <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                    isAnalyzed ? "bg-accent text-white" : "bg-neutral-200 text-neutral-500"
                  }`}>{n}</span>
                  <span className={`min-w-0 flex-1 truncate text-xs ${isAnalyzed ? "font-medium text-ink" : "text-neutral-500"}`}>
                    {summary?.oneLine ?? `Section ${n}`}
                  </span>
                  {isAnalyzed ? <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" /> : null}
                </div>
              );
            })}
          </div>
        )}

        {hoveredSummary ? (
          <div className="mt-3 rounded-md border border-accent/20 bg-blue-50 p-3">
            <p className="text-sm font-semibold text-ink">{hoveredSummary.oneLine}</p>
            {hoveredSummary.academic ? (
              <p className="mt-1 text-sm leading-6 text-neutral-700">{hoveredSummary.academic}</p>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}

// ─── Argument tab ─────────────────────────────────────────────────────────────

function ArgumentTab({
  synthesis,
  complete,
}: {
  synthesis: NonNullable<PaperMap["synthesis"]>;
  complete: boolean;
}) {
  const [showAll, setShowAll] = useState(false);
  const flow = synthesis.argument_flow;
  const visible = showAll ? flow : flow.slice(0, 8);
  const hidden = Math.max(0, flow.length - visible.length);

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div className="rounded-lg border border-line bg-panel p-5">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-semibold text-neutral-500">
            {complete ? "Full argument flow" : "Argument flow so far"}
          </p>
          {!complete ? (
            <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] font-semibold text-neutral-500">partial</span>
          ) : null}
        </div>

        {flow.length ? (
          <ol className="mt-4">
            {visible.map((step, i) => (
              <li key={step} className="flex gap-4">
                {/* connector */}
                <div className="flex flex-col items-center">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-50 text-[11px] font-semibold text-accent ring-1 ring-accent/20">
                    {i + 1}
                  </div>
                  {i < visible.length - 1 ? (
                    <div className="my-1 w-px flex-1 bg-accent/20" />
                  ) : null}
                </div>
                <div className={`min-w-0 pb-4 ${i === visible.length - 1 ? "pb-0" : ""}`}>
                  <p className="text-sm leading-6 text-neutral-800">{step}</p>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <p className="mt-4 text-sm text-neutral-400">Analyze more sections to build the argument flow.</p>
        )}

        {hidden ? (
          <button
            type="button"
            onClick={() => setShowAll(true)}
            className="mt-4 text-xs font-semibold text-accent hover:underline"
          >
            Show {hidden} more steps
          </button>
        ) : showAll && flow.length > 8 ? (
          <button
            type="button"
            onClick={() => setShowAll(false)}
            className="mt-4 text-xs font-semibold text-neutral-500 hover:underline"
          >
            Collapse
          </button>
        ) : null}
      </div>

      {synthesis.priority_concepts.length ? (
        <div className="rounded-lg border border-line bg-panel p-5">
          <p className="text-xs font-semibold text-neutral-500">Key concepts driving the argument</p>
          <div className="mt-4 space-y-4">
            {synthesis.priority_concepts.slice(0, 6).map((item) => (
              <div key={item.text} className="flex items-start gap-3">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                <div className="min-w-0">
                  <span className="text-sm font-semibold text-ink">{item.text}</span>
                  {item.sections.length ? (
                    <SectionRef sections={item.sections} />
                  ) : null}
                  <p className="mt-0.5 text-sm leading-5 text-neutral-600">{item.meaning}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

// ─── Concepts tab ─────────────────────────────────────────────────────────────

function ConceptsTab({ paperMap }: { paperMap: PaperMap }) {
  const allItems = [
    ...paperMap.top_concepts.map((i) => ({ ...i, kind: "concept" as const })),
    ...paperMap.top_terms.map((i) => ({ ...i, kind: "term" as const })),
  ];
  // Sort by how many sections they appear in (cross-reference value)
  const sorted = [...allItems].sort((a, b) => b.sections.length - a.sections.length || b.count - a.count);

  const [filter, setFilter] = useState<"all" | "concept" | "term">("all");
  const filtered = filter === "all" ? sorted : sorted.filter((i) => i.kind === filter);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold text-neutral-500">
          {sorted.length} items across {paperMap.analyzed_sections.length} sections
        </p>
        <div className="flex gap-1">
          {(["all", "concept", "term"] as const).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFilter(f)}
              className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${
                filter === f
                  ? "border-accent bg-accent text-white"
                  : "border-line bg-panel text-neutral-600 hover:bg-surface"
              }`}
            >
              {f === "all" ? "All" : f === "concept" ? "Concepts" : "Terms"}
            </button>
          ))}
        </div>
      </div>

      {filtered.length ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((item) => (
            <div
              key={`${item.kind}:${item.text}`}
              className="rounded-lg border border-line bg-panel p-4"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-semibold leading-5 text-ink">{item.text}</p>
                <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                  item.kind === "concept"
                    ? "bg-purple-50 text-purple-600"
                    : "bg-blue-50 text-accent"
                }`}>
                  {item.kind}
                </span>
              </div>
              {item.sections.length > 1 ? (
                <div className="mt-2 flex flex-wrap gap-1">
                  {item.sections.map((s) => (
                    <span key={s} className="rounded-full bg-neutral-100 px-1.5 py-0.5 text-[10px] font-semibold text-neutral-500">
                      §{s}
                    </span>
                  ))}
                </div>
              ) : null}
              <p className="mt-2 text-sm leading-5 text-neutral-600">{item.meaning}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-line bg-panel p-6 text-center text-sm text-neutral-400">
          Analyze more sections to build the concept map.
        </div>
      )}
    </div>
  );
}

// ─── Vocabulary tab ───────────────────────────────────────────────────────────

function VocabularyTab({ synthesis }: { synthesis: NonNullable<PaperMap["synthesis"]> }) {
  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_280px]">
      <div className="rounded-lg border border-line bg-panel p-5">
        <p className="text-xs font-semibold text-neutral-500">Priority terms</p>
        <div className="mt-4 space-y-4">
          {synthesis.priority_terms.slice(0, 8).map((item) => (
            <div key={item.text}>
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-semibold text-ink">{item.text}</p>
                <SectionRef sections={item.sections} />
              </div>
              <p className="mt-1 text-sm leading-5 text-neutral-600">{item.meaning}</p>
            </div>
          ))}
          {!synthesis.priority_terms.length ? <EmptyNote /> : null}
        </div>
      </div>
      <div className="rounded-lg border border-line bg-panel p-5">
        <p className="text-xs font-semibold text-neutral-500">Reusable expressions</p>
        <div className="mt-4 space-y-4">
          {synthesis.reusable_expressions.slice(0, 6).map((item) => (
            <div key={item.text}>
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-semibold text-ink">{item.text}</p>
                <SectionRef sections={item.sections} />
              </div>
              <p className="mt-1 text-sm leading-5 text-neutral-600">{item.meaning}</p>
            </div>
          ))}
          {!synthesis.reusable_expressions.length ? <EmptyNote /> : null}
        </div>
      </div>
      <div className="rounded-lg border border-line bg-panel p-5">
        <p className="text-xs font-semibold text-neutral-500">Review plan</p>
        {synthesis.review_plan.length ? (
          <ul className="mt-4 space-y-3">
            {synthesis.review_plan.map((item) => (
              <li key={item} className="flex items-start gap-2.5 text-sm leading-6 text-neutral-700">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                {item}
              </li>
            ))}
          </ul>
        ) : <EmptyNote />}
      </div>
    </div>
  );
}

// ─── Shared helpers ───────────────────────────────────────────────────────────

function SectionRef({ sections }: { sections: number[] }) {
  if (!sections.length) return null;
  return (
    <span className="ml-1 shrink-0 rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-accent">
      §{sections.slice(0, 4).join(" ")}
    </span>
  );
}

function EmptyNote() {
  return <p className="text-sm text-neutral-400">Analyze more sections to build this list.</p>;
}
