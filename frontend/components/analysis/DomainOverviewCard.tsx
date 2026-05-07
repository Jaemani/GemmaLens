import type { AnalysisResult } from "@/lib/types";
import { DifficultyBadge } from "./DifficultyBadge";

export function DomainOverviewCard({ analysis }: { analysis: AnalysisResult }) {
  return (
    <section className="rounded-lg border border-line bg-panel p-5 shadow-material">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-neutral-600">Domain</p>
          <h2 className="mt-1 text-2xl font-semibold capitalize">{analysis.domain.primary_domain}</h2>
          <p className="mt-2 text-sm text-neutral-600">{analysis.domain.secondary_domains.join(", ")}</p>
        </div>
        <DifficultyBadge level={analysis.difficulty.overall_level} />
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <Metric label="Lexical" value={analysis.difficulty.lexical_difficulty} />
        <Metric label="Syntax" value={analysis.difficulty.syntax_difficulty} />
        <Metric label="Domain" value={analysis.difficulty.domain_difficulty} />
      </div>
      <p className="mt-4 text-sm text-neutral-700">{analysis.difficulty.reason}</p>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-line p-3">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="mt-1 text-xl font-semibold">{value}/10</p>
    </div>
  );
}
