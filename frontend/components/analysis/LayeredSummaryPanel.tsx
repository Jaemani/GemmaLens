import type { AnalysisResult } from "@/lib/types";

export function LayeredSummaryPanel({ analysis }: { analysis: AnalysisResult }) {
  return (
    <section className="rounded-lg border border-line bg-panel p-5 shadow-material">
      <h2 className="text-lg font-semibold">Layered summaries</h2>
      <div className="mt-4 space-y-4 text-sm">
        <p><span className="font-semibold">One line:</span> {analysis.summaries.one_line}</p>
        <p><span className="font-semibold">Simple:</span> {analysis.summaries.simple}</p>
        <p><span className="font-semibold">Academic:</span> {analysis.summaries.academic}</p>
        <ul className="list-disc space-y-1 pl-5 text-neutral-700">
          {analysis.summaries.study_notes.map((note) => <li key={note}>{note}</li>)}
        </ul>
      </div>
    </section>
  );
}
