"use client";

import type { AnalysisResult } from "@/lib/types";
import { api } from "@/lib/api";

export function TermTable({ analysis }: { analysis: AnalysisResult }) {
  async function save(term: AnalysisResult["terms"][number]) {
    await api.saveDictionaryItem({
      item_type: "term",
      text: term.term,
      meaning: term.meaning,
      source_sentence: term.source_sentence,
      document_id: analysis.document_id
    });
  }

  return (
    <section className="overflow-hidden rounded-lg border border-line bg-panel shadow-material">
      <div className="border-b border-line p-5">
        <h2 className="text-lg font-semibold">Learning terms</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-surface text-xs uppercase text-neutral-500">
            <tr>
              <th className="px-4 py-3">Term</th>
              <th className="px-4 py-3">Meaning</th>
              <th className="px-4 py-3">Priority</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {analysis.terms.map((term) => (
              <tr key={term.term} className="border-t border-line">
                <td className="px-4 py-3 font-medium">{term.term}</td>
                <td className="px-4 py-3 text-neutral-700">{term.meaning}</td>
                <td className="px-4 py-3 capitalize">{term.domain_relevance}</td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => save(term)} className="rounded-md bg-accent px-3 py-2 text-xs font-semibold text-white">
                    Save
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
