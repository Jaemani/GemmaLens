"use client";

import type { AnalysisExperimentConfig, LabelVariant, ResultLayoutVariant, SaveModeVariant } from "@/lib/experiments";

type Props = {
  config: AnalysisExperimentConfig;
  onChange: (config: AnalysisExperimentConfig) => void;
};

export function ExperimentSwitchPanel({ config, onChange }: Props) {
  return (
    <section className="rounded-lg border border-line bg-panel p-4 shadow-material">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">A/B test controls</p>
          <p className="text-xs text-neutral-500">Default is all A. Changes stay in this browser.</p>
        </div>
        <span className="rounded-full bg-surface px-3 py-1 text-xs font-semibold text-neutral-700">
          {config.saveMode === "manual" && config.labelMode === "priority" && config.resultLayout === "tableFirst"
            ? "A baseline"
            : "Mixed variant"}
        </span>
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <SegmentedControl
          label="Save mode"
          value={config.saveMode}
          options={[
            { value: "manual", label: "A Manual" },
            { value: "autoHighPriority", label: "B Auto" }
          ]}
          onChange={(saveMode) => onChange({ ...config, saveMode })}
        />
        <SegmentedControl
          label="Labels"
          value={config.labelMode}
          options={[
            { value: "priority", label: "A Priority" },
            { value: "reason", label: "B Reason" }
          ]}
          onChange={(labelMode) => onChange({ ...config, labelMode })}
        />
        <SegmentedControl
          label="Layout"
          value={config.resultLayout}
          options={[
            { value: "tableFirst", label: "A Table" },
            { value: "readingContextFirst", label: "B Reader" }
          ]}
          onChange={(resultLayout) => onChange({ ...config, resultLayout })}
        />
      </div>
    </section>
  );
}

function SegmentedControl<T extends SaveModeVariant | LabelVariant | ResultLayoutVariant>({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: T;
  options: Array<{ value: T; label: string }>;
  onChange: (value: T) => void;
}) {
  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase text-neutral-500">{label}</p>
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
