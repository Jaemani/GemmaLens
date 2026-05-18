import { Loader2 } from "lucide-react";

const labels = [
  "Creating document record",
  "Extracting text and chunks",
  "Running model analysis",
  "Validating structured result",
  "Opening result"
];

export function AnalysisProgress({
  step,
  elapsed,
  title = "Analyzing document",
  currentLabel,
  labels: customLabels,
  hint
}: {
  step: number;
  elapsed: number;
  title?: string;
  currentLabel?: string | null;
  labels?: string[];
  hint?: string;
}) {
  const progressLabels = customLabels ?? labels;
  const activeIndex = Math.min(step, progressLabels.length - 1);
  const activeLabel = currentLabel ?? progressLabels[activeIndex];
  const defaultHint =
    step >= 2
      ? "Local model analysis is running. Warmed-up short tasks are faster; long documents still need staged analysis."
      : "Preparing the document before model analysis starts.";

  return (
    <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
      <div className="flex items-center gap-3">
        <Loader2 size={20} className="animate-spin text-accent" />
        <div>
          <h2 className="font-semibold text-ink">{title}</h2>
          <p className="text-sm text-neutral-600">
            {elapsed}s elapsed · {activeLabel}
          </p>
        </div>
      </div>
      <p className="mt-4 rounded-md bg-blue-50 px-3 py-2 text-sm text-accent">{hint ?? defaultHint}</p>
      <div className="mt-5 space-y-3">
        {progressLabels.map((label, index) => (
          <div key={label} className="flex items-center gap-3 text-sm">
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                index < activeIndex ? "bg-accent" : index === activeIndex ? "animate-pulse bg-accent" : "bg-line"
              }`}
            />
            <span className={index <= activeIndex ? "text-ink" : "text-neutral-500"}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
