"use client";

import { ChevronDown, ChevronRight, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { PaperMap } from "@/lib/types";

export function PaperMapProgressPanel({ documentId, refreshKey = 0 }: { documentId: string; refreshKey?: number }) {
  const [paperMap, setPaperMap] = useState<PaperMap | null>(null);
  const [loading, setLoading] = useState(true);
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
    next_steps: ["Analyze the next unstudied section."]
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
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line p-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Paper map</p>
          <h2 className="mt-1 text-lg font-semibold">{complete ? "Whole-paper learning guide" : "What this paper is teaching so far"}</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-neutral-600">
            {complete
              ? "Built from every analyzed section: argument flow, priority concepts, vocabulary, expressions, and review plan."
              : "Built from analyzed sections only. It grows as you analyze more sections, so it does not pretend the whole paper is complete."}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs font-semibold text-neutral-600">
            <span>
              {analyzedCount} / {totalSections} sections analyzed
            </span>
            <span className="h-2 w-36 overflow-hidden rounded-full bg-surface">
              <span className="block h-full rounded-full bg-accent" style={{ width: `${progress}%` }} />
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-xs font-semibold text-ink hover:bg-surface disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>
      <div className="grid gap-4 p-5">
        <div className="rounded-md border border-line bg-surface p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{guide.title}</p>
          <p className="mt-2 text-sm leading-6 text-ink">{guide.thesis_so_far}</p>
          <p className="mt-2 text-xs leading-5 text-neutral-600">{guide.coverage_note}</p>
          <div className="mt-4 grid gap-4">
            <GuideList title="Reading focus" rows={guide.reading_focus} />
            <GuideList title="Next steps" rows={guide.next_steps} />
          </div>
        </div>
        <SynthesisPanel synthesis={synthesis} />
        <div className="rounded-md border border-line bg-panel p-4">
          <button
            type="button"
            onClick={() => setShowSignals((value) => !value)}
            className="flex w-full items-center justify-between gap-3 text-left"
          >
            <span>
              <span className="block text-xs font-semibold uppercase tracking-wide text-neutral-500">Source-grounded signals</span>
              <span className="mt-1 block text-sm leading-6 text-neutral-600">
                Raw concepts, terms, and expressions behind the draft. Open when you want to inspect or save items.
              </span>
            </span>
            {showSignals ? <ChevronDown size={18} className="shrink-0 text-neutral-500" /> : <ChevronRight size={18} className="shrink-0 text-neutral-500" />}
          </button>
        </div>
        {showSignals ? (
          <>
            <MapList title="Concepts" rows={paperMap.top_concepts} />
            <MapList title="Terms" rows={paperMap.top_terms} />
            <MapList title="Expressions" rows={paperMap.top_phrases} />
          </>
        ) : null}
      </div>
      <div className="border-t border-line p-5">
        <button
          type="button"
          onClick={() => setShowSectionSummaries((value) => !value)}
          className="flex w-full items-center justify-between gap-3 text-left"
        >
          <span>
            <span className="block text-xs font-semibold uppercase tracking-wide text-neutral-500">Analyzed sections</span>
            <span className="mt-1 block text-sm leading-6 text-neutral-600">
              {paperMap.section_summaries.length
                ? `${paperMap.section_summaries.length} section summaries are available. Open when you want to audit the section-by-section trail.`
                : "Analyze a section to start building the paper map."}
            </span>
          </span>
          {showSectionSummaries ? (
            <ChevronDown size={18} className="shrink-0 text-neutral-500" />
          ) : (
            <ChevronRight size={18} className="shrink-0 text-neutral-500" />
          )}
        </button>
        {showSectionSummaries && paperMap.section_summaries.length ? (
          <div className="mt-3 grid gap-3">
            {paperMap.section_summaries.map((summary) => (
              <article key={summary.text} className="rounded-md border border-line bg-surface p-3">
                <p className="text-sm font-semibold text-ink">{summary.text}</p>
                <p className="mt-1 text-xs leading-5 text-neutral-600">{summary.meaning}</p>
              </article>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}

function SynthesisPanel({ synthesis }: { synthesis: NonNullable<PaperMap["synthesis"]> }) {
  return (
    <div className="rounded-md border border-line bg-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Whole-paper learning draft</p>
        <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-semibold text-neutral-500">{synthesis.status}</span>
      </div>
      <GuideList title="Argument flow" rows={synthesis.argument_flow} />
      <div className="mt-4 grid gap-4">
        <SynthesisList title="Priority concepts" rows={synthesis.priority_concepts} limit={6} />
        <SynthesisList title="Priority terms" rows={synthesis.priority_terms} limit={8} />
        <SynthesisList title="Reusable expressions" rows={synthesis.reusable_expressions} limit={6} />
      </div>
      <GuideList title="Review plan" rows={synthesis.review_plan} />
    </div>
  );
}

function SynthesisList({ title, rows, limit }: { title: string; rows: PaperMap["top_terms"]; limit: number }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{title}</p>
      {rows.length ? (
        <div className="mt-2 space-y-3">
          {rows.slice(0, limit).map((row) => (
            <div key={row.text} className="border-t border-line pt-3 first:border-t-0 first:pt-0">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-semibold text-ink">{row.text}</p>
                <span className="shrink-0 text-[11px] font-semibold text-neutral-500">S{row.sections.join(", ")}</span>
              </div>
              <p className="mt-1 line-clamp-2 text-xs leading-5 text-neutral-600">{row.meaning}</p>
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
