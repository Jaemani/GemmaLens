"use client";

import { ChevronDown, ChevronRight, RefreshCw, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { PaperMap } from "@/lib/types";

export function PaperMapProgressPanel({ documentId, refreshKey = 0 }: { documentId: string; refreshKey?: number }) {
  const [paperMap, setPaperMap] = useState<PaperMap | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [showStudyLists, setShowStudyLists] = useState(true);
  const [showSignals, setShowSignals] = useState(false);
  const [showSectionSummaries, setShowSectionSummaries] = useState(false);

  async function load() {
    setLoading(true);
    try {
      setPaperMap(await api.getPaperMap(documentId));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [documentId, refreshKey]);

  useEffect(() => {
    if (!expanded) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setExpanded(false);
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [expanded]);

  if (!paperMap && loading) {
    return (
      <section className="rounded-lg border border-line bg-panel p-5 text-sm text-neutral-600 shadow-material">
        Loading paper map...
      </section>
    );
  }
  if (!paperMap) return null;

  const analyzedCount = paperMap.analyzed_sections.length;
  const totalSections = paperMap.total_sections || Math.max(analyzedCount, 1);
  const progress = totalSections ? Math.min(100, Math.round((analyzedCount / totalSections) * 100)) : 0;
  const complete = Boolean(totalSections && analyzedCount >= totalSections);
  const guide = paperMap.guide ?? {
    title: "Reading guide",
    thesis_so_far: analyzedCount ? "This map is built from analyzed sections only." : "No section has been analyzed yet.",
    coverage_note: `${analyzedCount} / ${totalSections} sections analyzed.`,
    reading_focus: [],
    next_steps: ["Analyze the next section without a lesson."]
  };
  const synthesis = paperMap.synthesis ?? {
    status: "partial",
    argument_flow: [],
    priority_concepts: paperMap.top_concepts.slice(0, 5),
    priority_terms: paperMap.top_terms.slice(0, 8),
    reusable_expressions: paperMap.top_phrases.slice(0, 6),
    review_plan: []
  };

  return (
    <section className="rounded-lg border border-line bg-panel shadow-material">
      <div className="p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{complete ? "Paper study map" : "Progressive paper map"}</p>
          <h2 className="mt-1 text-base font-semibold">{complete ? "Whole-paper guide ready" : "Map from ready sections"}</h2>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-neutral-600">
            {complete
              ? "Complete section-level map for the paper: reading guide, argument flow, priority concepts, and review material."
              : "Auto-refreshes as section lessons finish. Expand when you want the argument flow and priority concepts."}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="inline-flex items-center gap-1.5 rounded-md border border-line bg-panel px-2.5 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-surface"
        >
          <ChevronRight size={14} />
          Open map
        </button>
        </div>
        {!complete ? (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <>
              <span className="h-2 w-36 overflow-hidden rounded-full bg-surface">
                <span className="block h-full rounded-full bg-accent" style={{ width: `${progress}%` }} />
              </span>
              <span className="text-xs font-semibold text-neutral-600">{progress}% mapped</span>
            </>
            <button
              type="button"
              onClick={load}
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-md border border-line px-2.5 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-surface disabled:opacity-50"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
              Refresh
            </button>
          </div>
        ) : null}
      </div>
      {expanded ? (
        <PaperMapWorkspace
          complete={complete}
          guide={guide}
          synthesis={synthesis}
          paperMap={paperMap}
          showStudyLists={showStudyLists}
          setShowStudyLists={setShowStudyLists}
          showSignals={showSignals}
          setShowSignals={setShowSignals}
          showSectionSummaries={showSectionSummaries}
          setShowSectionSummaries={setShowSectionSummaries}
          onClose={() => setExpanded(false)}
        />
      ) : null}
    </section>
  );
}

function PaperMapWorkspace({
  complete,
  guide,
  synthesis,
  paperMap,
  showStudyLists,
  setShowStudyLists,
  showSignals,
  setShowSignals,
  showSectionSummaries,
  setShowSectionSummaries,
  onClose
}: {
  complete: boolean;
  guide: NonNullable<PaperMap["guide"]>;
  synthesis: NonNullable<PaperMap["synthesis"]>;
  paperMap: PaperMap;
  showStudyLists: boolean;
  setShowStudyLists: (value: (current: boolean) => boolean) => void;
  showSignals: boolean;
  setShowSignals: (value: (current: boolean) => boolean) => void;
  showSectionSummaries: boolean;
  setShowSectionSummaries: (value: (current: boolean) => boolean) => void;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 bg-ink/30 px-4 py-6 backdrop-blur-sm" role="dialog" aria-modal="true">
      <div className="mx-auto flex h-[min(88vh,980px)] w-[min(1180px,94vw)] flex-col overflow-hidden rounded-lg border border-line bg-panel shadow-material">
        <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{complete ? "Paper study map" : "Progressive paper map"}</p>
            <h2 className="mt-1 text-xl font-semibold text-ink">{complete ? "Whole-paper guide ready" : "Map from ready sections"}</h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-neutral-600">{guide.coverage_note}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-line text-neutral-600 hover:bg-surface"
            aria-label="Close paper map"
          >
            <X size={17} />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto bg-surface p-5">
          <div className="grid gap-5 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <div className="rounded-md border border-line bg-panel p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{guide.title}</p>
              <p className="mt-2 text-base leading-7 text-ink">{guide.thesis_so_far}</p>
              <div className="mt-5 grid gap-5 md:grid-cols-2 xl:grid-cols-1">
                <GuideList title="Reading focus" rows={guide.reading_focus.slice(0, 3)} />
                <GuideList title="Next steps" rows={guide.next_steps.slice(0, 3)} />
              </div>
            </div>
            <SynthesisPanel synthesis={synthesis} complete={complete} />
          </div>

          <div className="mt-5 rounded-md border border-line bg-panel p-4">
            <button
              type="button"
              onClick={() => setShowStudyLists((value) => !value)}
              className="flex w-full items-center justify-between gap-3 text-left"
            >
              <span>
                <span className="block text-xs font-semibold uppercase tracking-wide text-neutral-500">Vocabulary and review plan</span>
                <span className="mt-1 block text-sm leading-6 text-neutral-600">Paper-level terms, reusable expressions, and review sequence.</span>
              </span>
              {showStudyLists ? <ChevronDown size={18} className="shrink-0 text-neutral-500" /> : <ChevronRight size={18} className="shrink-0 text-neutral-500" />}
            </button>
          </div>
          {showStudyLists ? (
            <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_320px]">
              <div className="rounded-md border border-line bg-panel p-4">
                <SynthesisList title="Priority terms" rows={synthesis.priority_terms} limit={8} spacious />
              </div>
              <div className="rounded-md border border-line bg-panel p-4">
                <SynthesisList title="Reusable expressions" rows={synthesis.reusable_expressions} limit={6} spacious />
              </div>
              <div className="rounded-md border border-line bg-panel p-4">
                <GuideList title="Review plan" rows={synthesis.review_plan} />
              </div>
            </div>
          ) : null}

          <div className="mt-5 grid gap-4 xl:grid-cols-2">
            <DisclosureBlock
              title="Source-grounded signals"
              detail="Raw concepts, terms, and expressions behind the draft."
              open={showSignals}
              onToggle={() => setShowSignals((value) => !value)}
            />
            <DisclosureBlock
              title="Analyzed sections"
              detail={`${paperMap.section_summaries.length} section summaries are available for audit.`}
              open={showSectionSummaries}
              onToggle={() => setShowSectionSummaries((value) => !value)}
            />
          </div>
          {showSignals ? (
            <div className="mt-4 grid gap-4 xl:grid-cols-3">
              <MapList title="Concepts" rows={paperMap.top_concepts} />
              <MapList title="Terms" rows={paperMap.top_terms} />
              <MapList title="Expressions" rows={paperMap.top_phrases} />
            </div>
          ) : null}
          {showSectionSummaries && paperMap.section_summaries.length ? (
            <div className="mt-4 grid gap-3 xl:grid-cols-2">
              {paperMap.section_summaries.map((summary) => (
                <article key={summary.text} className="rounded-md border border-line bg-panel p-3">
                  <p className="text-sm font-semibold text-ink">{summary.text}</p>
                  <p className="mt-1 text-xs leading-5 text-neutral-600">{summary.meaning}</p>
                </article>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function DisclosureBlock({ title, detail, open, onToggle }: { title: string; detail: string; open: boolean; onToggle: () => void }) {
  return (
    <div className="rounded-md border border-line bg-panel p-4">
      <button type="button" onClick={onToggle} className="flex w-full items-center justify-between gap-3 text-left">
        <span>
          <span className="block text-xs font-semibold uppercase tracking-wide text-neutral-500">{title}</span>
          <span className="mt-1 block text-sm leading-6 text-neutral-600">{detail}</span>
        </span>
        {open ? <ChevronDown size={18} className="shrink-0 text-neutral-500" /> : <ChevronRight size={18} className="shrink-0 text-neutral-500" />}
      </button>
    </div>
  );
}

function SynthesisPanel({ synthesis, complete }: { synthesis: NonNullable<PaperMap["synthesis"]>; complete: boolean }) {
  const [showFullFlow, setShowFullFlow] = useState(false);
  const visibleFlow = showFullFlow ? synthesis.argument_flow : synthesis.argument_flow.slice(0, 5);
  const hiddenFlowCount = Math.max(0, synthesis.argument_flow.length - visibleFlow.length);
  const title = complete ? "Argument map" : "Draft argument map";

  return (
    <div className="rounded-md border border-line bg-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{title}</p>
        <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-semibold text-neutral-500">{synthesis.status}</span>
      </div>
      <div className="mt-3 max-h-56 overflow-y-auto rounded-md border border-line bg-panel p-3">
        <GuideList title="Argument flow" rows={visibleFlow} />
      </div>
      {hiddenFlowCount ? (
        <button
          type="button"
          onClick={() => setShowFullFlow(true)}
          className="mt-2 rounded-md border border-line bg-panel px-3 py-2 text-xs font-semibold text-ink hover:bg-white"
        >
          Show {hiddenFlowCount} more sections
        </button>
      ) : showFullFlow && synthesis.argument_flow.length > 6 ? (
        <button
          type="button"
          onClick={() => setShowFullFlow(false)}
          className="mt-2 rounded-md border border-line bg-panel px-3 py-2 text-xs font-semibold text-ink hover:bg-white"
        >
          Collapse argument flow
        </button>
      ) : null}
      <div className="mt-4 rounded-md border border-line bg-panel p-3">
        <SynthesisList title="Priority concepts" rows={synthesis.priority_concepts} limit={6} />
      </div>
    </div>
  );
}

function SynthesisList({ title, rows, limit, spacious = false }: { title: string; rows: PaperMap["top_terms"]; limit: number; spacious?: boolean }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{title}</p>
      {rows.length ? (
        <div className={spacious ? "mt-3 space-y-3" : "mt-2 space-y-3"}>
          {rows.slice(0, limit).map((row) => (
            <div
              key={row.text}
              className={
                spacious
                  ? "rounded-md border border-line bg-panel px-3 py-3"
                  : "border-t border-line pt-3 first:border-t-0 first:pt-0"
              }
            >
              <div className="flex items-start justify-between gap-3">
                <p className={spacious ? "min-w-0 text-base font-semibold leading-6 text-ink" : "text-sm font-semibold text-ink"}>{row.text}</p>
                <span
                  className={
                    spacious
                      ? "shrink-0 rounded-full bg-blue-50 px-2 py-1 text-[11px] font-semibold text-accent"
                      : "shrink-0 text-[11px] font-semibold text-neutral-500"
                  }
                >
                  S{row.sections.join(", ")}
                </span>
              </div>
              <p className={spacious ? "mt-2 text-sm leading-6 text-neutral-700" : "mt-1 line-clamp-2 text-xs leading-5 text-neutral-600"}>{row.meaning}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-2 text-xs leading-5 text-neutral-600">Analyze more sections to build this list.</p>
      )}
    </div>
  );
}

function GuideList({ title, rows }: { title: string; rows: string[] }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{title}</p>
      {rows.length ? (
        <ul className="mt-2 space-y-2">
          {rows.map((row) => (
            <li key={row} className="text-xs leading-5 text-neutral-700">
              {row}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-xs leading-5 text-neutral-600">Analyze more sections to build this guide.</p>
      )}
    </div>
  );
}

function MapList({ title, rows }: { title: string; rows: PaperMap["top_terms"] }) {
  return (
    <div className="rounded-md border border-line bg-surface p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{title}</p>
      {rows.length ? (
        <div className="mt-3 space-y-3">
          {rows.slice(0, 6).map((row) => (
            <div key={row.text}>
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-semibold text-ink">{row.text}</p>
                <span className="shrink-0 rounded-full bg-white px-2 py-0.5 text-[11px] font-semibold text-neutral-500">
                  S{row.sections.join(", ")}
                </span>
              </div>
              <p className="mt-1 line-clamp-2 text-xs leading-5 text-neutral-600">{row.meaning}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm text-neutral-600">No saved section signal yet.</p>
      )}
    </div>
  );
}
