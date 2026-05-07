import type { AnalysisResult } from "@/lib/types";

export function SentenceDecompositionCard({ sentence }: { sentence: AnalysisResult["sentences"][number] }) {
  return (
    <article className="rounded-lg border border-line bg-panel p-5 shadow-material">
      <p className="text-sm text-neutral-700">{sentence.sentence}</p>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <Block label="Core structure" value={sentence.core_structure} />
        <Block label="Simplified" value={sentence.simplified_version} />
        <Block label="Korean explanation" value={sentence.korean_explanation} />
        <Block label="Difficulty" value={sentence.difficulty_reason} />
      </div>
    </article>
  );
}

function Block({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-surface p-3">
      <p className="text-xs font-semibold uppercase text-neutral-500">{label}</p>
      <p className="mt-1 text-sm">{value}</p>
    </div>
  );
}
