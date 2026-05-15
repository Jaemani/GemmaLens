"use client";

import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { DEMO_DOCUMENT_ID } from "@/lib/demoData";
import type { AnalysisResult } from "@/lib/types";

type SourceKind = "document" | "video";

export function ConceptMapPanel({ analysis, sourceKind = "document" }: { analysis: AnalysisResult; sourceKind?: SourceKind }) {
  const concepts = useMemo(() => analysis.concepts ?? [], [analysis.concepts]);
  const [saved, setSaved] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState<string | null>(null);

  async function saveConcept(concept: NonNullable<AnalysisResult["concepts"]>[number]) {
    setSaving(concept.concept);
    try {
      if (analysis.document_id !== DEMO_DOCUMENT_ID) {
        await api.saveDictionaryItem({
          item_type: "concept",
          text: concept.concept,
          meaning: concept.explanation,
          source_sentence: concept.source_sentence,
          document_id: analysis.document_id
        });
      }
      setSaved((current) => new Set(current).add(concept.concept));
    } finally {
      setSaving(null);
    }
  }

  if (!concepts.length) return null;

  const copy =
    sourceKind === "video"
      ? {
          eyebrow: "Video learning map",
          title: "Concepts and expressions in this transcript",
          description: "Concepts explain what this segment is teaching. Terms and phrases below help you follow the spoken explanation."
        }
      : {
          eyebrow: "Paper map",
          title: "Concepts to understand before memorizing words",
          description: "Concepts explain the argument of the paper. Terms and phrases below explain the language used to express those ideas."
        };

  return (
    <section className="rounded-lg border border-line bg-panel shadow-material">
      <div className="border-b border-line p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{copy.eyebrow}</p>
        <h2 className="mt-1 text-lg font-semibold">{copy.title}</h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-neutral-600">{copy.description}</p>
      </div>
      <div className="grid gap-4 p-5 md:grid-cols-2">
        {concepts.map((concept) => {
          const isSaved = saved.has(concept.concept);
          return (
            <article key={concept.concept} className="rounded-lg border border-line bg-surface p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-ink">{concept.concept}</h3>
                  <p className="mt-2 text-sm leading-6 text-neutral-700">{concept.explanation}</p>
                </div>
                <button
                  type="button"
                  onClick={() => saveConcept(concept)}
                  disabled={isSaved || saving === concept.concept}
                  className="shrink-0 rounded-md bg-accent px-3 py-2 text-xs font-semibold text-white disabled:bg-line disabled:text-neutral-600"
                >
                  {isSaved ? "Saved" : saving === concept.concept ? "Saving" : "Save"}
                </button>
              </div>
              <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">Why it matters</p>
              <p className="mt-1 text-sm leading-6 text-neutral-700">{concept.why_it_matters}</p>
              {concept.related_terms.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {concept.related_terms.slice(0, 6).map((term) => (
                    <span key={term} className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-neutral-600">
                      {term}
                    </span>
                  ))}
                </div>
              ) : null}
              <p className="mt-3 max-h-28 overflow-y-auto rounded-md bg-white p-3 text-xs leading-5 text-neutral-600">{concept.source_sentence}</p>
              {concept.references.length ? (
                <p className="mt-2 text-xs text-neutral-500">References: {concept.references.join(", ")}</p>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
