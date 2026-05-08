"use client";

import { SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import type { AnalysisExperimentConfig, LabelVariant, ResultLayoutVariant, SaveModeVariant } from "@/lib/experiments";

type Props = {
  config: AnalysisExperimentConfig;
  onChange: (config: AnalysisExperimentConfig) => void;
};

export function ExperimentSwitchPanel({ config, onChange }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <section className="rounded-lg border border-line bg-panel p-4 shadow-material">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">A/B test panel</p>
          <p className="text-xs text-neutral-500">Default is all A. Use this panel for team feedback sessions.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-surface px-3 py-1 text-xs font-semibold text-neutral-700">
            {config.saveMode === "manual" && config.labelMode === "priority" && config.resultLayout === "tableFirst"
              ? "A baseline"
              : "Mixed variant"}
          </span>
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-xs font-semibold hover:bg-surface"
          >
            <SlidersHorizontal size={15} />
            {open ? "Hide" : "Show"}
          </button>
        </div>
      </div>
      {open ? (
        <div className="mt-4 grid gap-3 lg:grid-cols-3">
          <SegmentedControl
            label="Save mode"
            detail="A: user chooses saved items. B: app auto-saves high-priority items."
            value={config.saveMode}
            options={[
              { value: "manual", label: "A Manual" },
              { value: "autoHighPriority", label: "B Auto" }
            ]}
            onChange={(saveMode) => onChange({ ...config, saveMode })}
          />
          <SegmentedControl
            label="Labels"
            detail="A: learning priority. B: why this item was shown."
            value={config.labelMode}
            options={[
              { value: "priority", label: "A Priority" },
              { value: "reason", label: "B Reason" }
            ]}
            onChange={(labelMode) => onChange({ ...config, labelMode })}
          />
          <SegmentedControl
            label="Layout"
            detail="A: cleanup table first. B: reading context first."
            value={config.resultLayout}
            options={[
              { value: "tableFirst", label: "A Table" },
              { value: "readingContextFirst", label: "B Reader" }
            ]}
            onChange={(resultLayout) => onChange({ ...config, resultLayout })}
          />
        </div>
      ) : null}
    </section>
  );
}

function SegmentedControl<T extends SaveModeVariant | LabelVariant | ResultLayoutVariant>({
  label,
  detail,
  value,
  options,
  onChange
}: {
  label: string;
  detail: string;
  value: T;
  options: Array<{ value: T; label: string }>;
  onChange: (value: T) => void;
}) {
  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase text-neutral-500">{label}</p>
      <p className="mb-2 min-h-8 text-xs leading-4 text-neutral-600">{detail}</p>
      <div className="grid grid-cols-2 rounded-lg border border-line bg-surface p-1">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={`rounded-md px-3 py-2 text-xs font-semibold transition ${
              option.value === value ? "bg-panel text-accent shadow-material" : "text-neutral-600 hover:text-ink"
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
