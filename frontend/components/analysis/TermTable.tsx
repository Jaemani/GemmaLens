"use client";

import { useMemo, useState } from "react";
import type { AnalysisResult } from "@/lib/types";
import { api } from "@/lib/api";
import type { AnalysisExperimentConfig } from "@/lib/experiments";
import { DEMO_DOCUMENT_ID } from "@/lib/demoData";

type Row = {
  key: string;
  type: "term" | "phrase";
  text: string;
  meaning: string;
  source_sentence: string;
  priorityLabel: string;
  reasonLabel: string;
  highPriority: boolean;
  reviewStates: string[];
};

export function TermTable({ analysis, config }: { analysis: AnalysisResult; config: AnalysisExperimentConfig }) {
  const [savedKeys, setSavedKeys] = useState<Set<string>>(new Set());
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const rows = useMemo(() => buildRows(analysis), [analysis]);

  async function save(row: Row) {
    setSavingKey(row.key);
    try {
      if (analysis.document_id !== DEMO_DOCUMENT_ID) {
        await api.saveDictionaryItem({
          item_type: row.type,
          text: row.text,
          meaning: row.meaning,
          source_sentence: row.source_sentence,
          document_id: analysis.document_id
        });
      }
      setSavedKeys((current) => new Set(current).add(row.key));
    } finally {
      setSavingKey(null);
    }
  }

  return (
    <section className="overflow-hidden rounded-lg border border-line bg-panel shadow-material">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line p-5">
        <div>
          <h2 className="text-lg font-semibold">Learning objects</h2>
          <p className="mt-1 text-sm text-neutral-600">
            {analysis.document_id === DEMO_DOCUMENT_ID
              ? "Demo save state is local to this browser tab."
              : config.saveMode === "manual"
                ? "Manual save baseline. User chooses what enters the dictionary."
                : "High-priority items can be auto-saved for comparison."}
          </p>
        </div>
        <span className="rounded-full bg-surface px-3 py-1 text-xs font-semibold text-neutral-600">
          {config.labelMode === "priority" ? "A priority labels" : "B reason labels"}
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-surface text-xs uppercase text-neutral-500">
            <tr>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Item</th>
              <th className="px-4 py-3">Meaning</th>
              <th className="px-4 py-3">{config.labelMode === "priority" ? "Priority" : "Why shown"}</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} className="border-t border-line align-top">
                <td className="px-4 py-3 capitalize text-neutral-500">{row.type}</td>
                <td className="px-4 py-3">
                  <p className="font-medium">{row.text}</p>
                  {config.itemDetail === "learningCard" ? (
                    <div className="mt-3 space-y-2 rounded-md bg-surface p-3 text-xs leading-5 text-neutral-700">
                      <p>
                        <span className="font-semibold text-ink">Context:</span> {row.source_sentence}
                      </p>
                      <p>
                        <span className="font-semibold text-ink">Why:</span> {row.reasonLabel}
                      </p>
                    </div>
                  ) : null}
                </td>
                <td className="max-w-md px-4 py-3 text-neutral-700">
                  {row.meaning}
                  {config.reviewState === "study" ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {row.reviewStates.map((state) => (
                        <button key={state} type="button" className="rounded-full border border-line px-2.5 py-1 text-xs font-semibold text-neutral-600 hover:bg-surface">
                          {state}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {["New", "Viewed", "Familiar"].map((state) => (
                        <button key={state} type="button" className="rounded-full border border-line px-2.5 py-1 text-xs font-semibold text-neutral-600 hover:bg-surface">
                          {state}
                        </button>
                      ))}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${row.highPriority ? "bg-blue-100 text-accent" : "bg-surface text-neutral-600"}`}>
                    {config.labelMode === "priority" ? row.priorityLabel : row.reasonLabel}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => save(row)}
                    disabled={savedKeys.has(row.key) || savingKey === row.key}
                    className="rounded-md bg-accent px-3 py-2 text-xs font-semibold text-white disabled:bg-line disabled:text-neutral-600"
                  >
                    {savedKeys.has(row.key) ? "Saved" : savingKey === row.key ? "Saving" : "Save"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function buildRows(analysis: AnalysisResult): Row[] {
  return [
    ...analysis.terms.map((term): Row => {
      const highPriority = term.should_save || term.domain_relevance === "high" || term.difficulty === "hard";
      return {
        key: `term:${term.term}`,
        type: "term",
        text: term.term,
        meaning: term.meaning,
        source_sentence: term.source_sentence,
        priorityLabel: highPriority ? "Must know" : term.domain_relevance === "medium" ? "Useful here" : "Low priority",
        reasonLabel: term.domain_relevance === "high" ? "Important field term" : term.difficulty === "hard" ? "Blocks understanding" : "Useful in context",
        highPriority,
        reviewStates: ["Review soon", "Mastered", "Ignore"]
      };
    }),
    ...analysis.phrases.map((phrase): Row => {
      const highPriority = phrase.function !== "general";
      return {
        key: `phrase:${phrase.phrase}`,
        type: "phrase",
        text: phrase.phrase,
        meaning: phrase.explanation,
        source_sentence: phrase.source_sentence,
        priorityLabel: highPriority ? "Useful expression" : "Low priority",
        reasonLabel: phrase.function === "general" ? "Structure pattern" : `Academic ${phrase.function}`,
        highPriority,
        reviewStates: ["Review soon", "Mastered", "Ignore"]
      };
    })
  ];
}
