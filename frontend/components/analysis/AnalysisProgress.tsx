import { Loader2 } from "lucide-react";

const labels = [
  "Creating document record",
  "Extracting text and chunks",
  "Running model analysis",
  "Validating structured result",
  "Opening result"
];

export function AnalysisProgress({ step, elapsed }: { step: number; elapsed: number }) {
  return (
    <div className="rounded-2xl border border-line bg-panel p-5 shadow-material">
      <div className="flex items-center gap-3">
        <Loader2 size={20} className="animate-spin text-accent" />
        <div>
          <h2 className="font-semibold text-ink">Analyzing document</h2>
          <p className="text-sm text-neutral-600">{elapsed}s elapsed</p>
        </div>
      </div>
      <div className="mt-5 space-y-3">
        {labels.map((label, index) => (
          <div key={label} className="flex items-center gap-3 text-sm">
            <span className={`h-2.5 w-2.5 rounded-full ${index <= step ? "bg-accent" : "bg-line"}`} />
            <span className={index <= step ? "text-ink" : "text-neutral-500"}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
