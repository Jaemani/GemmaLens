"use client";

import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { PaperMap } from "@/lib/types";

export function PaperMapProgressPanel({ documentId, refreshKey = 0 }: { documentId: string; refreshKey?: number }) {
  const [paperMap, setPaperMap] = useState<PaperMap | null>(null);
  const [loading, setLoading] = useState(true);

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
  const guide = paperMap.guide ?? {
    title: "Reading guide",
    thesis_so_far: analyzedCount ? "This map is built from analyzed sections only." : "No section has been analyzed yet.",
    coverage_note: `${analyzedCount} / ${totalSections} sections analyzed.`,
    reading_focus: [],
    next_steps: ["Analyze the next unstudied section."]
  };

  return (
    <section className="rounded-lg border border-line bg-panel shadow-material">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line p-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Paper map</p>
          <h2 className="mt-1 text-lg font-semibold">What this paper is teaching so far</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-neutral-600">
            Built from analyzed sections only. It grows as you analyze more sections, so it does not pretend the whole paper is complete.
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
      <div className="grid gap-4 p-5 lg:grid-cols-3">
        <div className="rounded-md border border-line bg-surface p-4 lg:col-span-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{guide.title}</p>
          <p className="mt-2 text-sm leading-6 text-ink">{guide.thesis_so_far}</p>
          <p className="mt-2 text-xs leading-5 text-neutral-600">{guide.coverage_note}</p>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <GuideList title="Reading focus" rows={guide.reading_focus} />
            <GuideList title="Next steps" rows={guide.next_steps} />
          </div>
        </div>
        <MapList title="Concepts" rows={paperMap.top_concepts} />
        <MapList title="Terms" rows={paperMap.top_terms} />
        <MapList title="Expressions" rows={paperMap.top_phrases} />
      </div>
      <div className="border-t border-line p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Analyzed sections</p>
        {paperMap.section_summaries.length ? (
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {paperMap.section_summaries.map((summary) => (
              <article key={summary.text} className="rounded-md border border-line bg-surface p-3">
                <p className="text-sm font-semibold text-ink">{summary.text}</p>
                <p className="mt-1 text-xs leading-5 text-neutral-600">{summary.meaning}</p>
              </article>
            ))}
          </div>
        ) : (
          <p className="mt-2 text-sm text-neutral-600">Analyze a section to start building the paper map.</p>
        )}
      </div>
    </section>
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
