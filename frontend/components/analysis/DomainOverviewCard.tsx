import type { AnalysisResult } from "@/lib/types";
import { DifficultyBadge } from "./DifficultyBadge";

export function DomainOverviewCard({ analysis }: { analysis: AnalysisResult }) {
  const reason = userFacingDifficultyReason(analysis.difficulty.reason);
  return (
    <section className="rounded-lg border border-line bg-panel px-4 py-3 shadow-material">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Reading profile</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold capitalize">{analysis.domain.primary_domain}</h2>
            <DifficultyBadge level={analysis.difficulty.overall_level} />
          </div>
          {analysis.domain.secondary_domains.length ? (
            <p className="mt-1 text-xs text-neutral-600">{analysis.domain.secondary_domains.join(", ")}</p>
          ) : null}
        </div>
        <div className="grid min-w-[280px] flex-1 gap-2 sm:max-w-xl sm:grid-cols-3">
          <Metric label="Lexical" value={analysis.difficulty.lexical_difficulty} />
          <Metric label="Syntax" value={analysis.difficulty.syntax_difficulty} />
          <Metric label="Domain" value={analysis.difficulty.domain_difficulty} />
        </div>
      </div>
      {reason ? <p className="mt-2 text-xs leading-5 text-neutral-600">{reason}</p> : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-line bg-surface px-3 py-2">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="mt-0.5 text-base font-semibold">{value}/10</p>
    </div>
  );
}

function userFacingDifficultyReason(reason: string) {
  const lowered = reason.toLowerCase();
  if (lowered.includes("code-generated") || lowered.includes("model-generated") || lowered.includes("fast edge mode")) {
    return "Difficulty is calibrated against the selected reading level and refined by the section learning guide below.";
  }
  return reason;
}
