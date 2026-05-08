"use client";

import { SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import {
  isBaselineA,
  type AnalysisExperimentConfig,
  type ItemDetailVariant,
  type LabelVariant,
  type ResultLayoutVariant,
  type ReviewStateVariant,
  type SaveModeVariant,
  type UserFitVariant
} from "@/lib/experiments";

type Props = {
  config: AnalysisExperimentConfig;
  onChange: (config: AnalysisExperimentConfig) => void;
  defaultOpen?: boolean;
};

export function ExperimentSwitchPanel({ config, onChange, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="rounded-lg border border-line bg-panel p-4 shadow-material">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">A/B test panel</p>
          <p className="text-xs text-neutral-500">Controls all documented variants. Changes stay in this browser.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-surface px-3 py-1 text-xs font-semibold text-neutral-700">
            {isBaselineA(config) ? "All A baseline" : "Mixed variant"}
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
        <div className="mt-4 grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
          <SegmentedControl
            label="1. Dictionary save"
            detail="A: user chooses saved items. B: app auto-saves high-priority items."
            value={config.saveMode}
            options={[
              { value: "manual", label: "A Manual" },
              { value: "autoHighPriority", label: "B Auto" }
            ]}
            onChange={(saveMode) => onChange({ ...config, saveMode })}
          />
          <SegmentedControl
            label="2. Highlight labels"
            detail="A: learning priority. B: why this item was shown."
            value={config.labelMode}
            options={[
              { value: "priority", label: "A Priority" },
              { value: "reason", label: "B Reason" }
            ]}
            onChange={(labelMode) => onChange({ ...config, labelMode })}
          />
          <SegmentedControl
            label="3. Result layout"
            detail="A: cleanup table first. B: reading context first."
            value={config.resultLayout}
            options={[
              { value: "tableFirst", label: "A Table" },
              { value: "readingContextFirst", label: "B Reader" }
            ]}
            onChange={(resultLayout) => onChange({ ...config, resultLayout })}
          />
          <SegmentedControl
            label="4. Item detail"
            detail="A: compact item. B: expanded learning card details."
            value={config.itemDetail}
            options={[
              { value: "compact", label: "A Compact" },
              { value: "learningCard", label: "B Card" }
            ]}
            onChange={(itemDetail) => onChange({ ...config, itemDetail })}
          />
          <SegmentedControl
            label="5. Review state"
            detail="A: New/Viewed/Familiar. B: Review soon/Mastered/Ignore."
            value={config.reviewState}
            options={[
              { value: "simple", label: "A Simple" },
              { value: "study", label: "B Study" }
            ]}
            onChange={(reviewState) => onChange({ ...config, reviewState })}
          />
          <SegmentedControl
            label="6. User fit"
            detail="A: ask up front. B: learn from save/ignore/view actions."
            value={config.userFit}
            options={[
              { value: "onboarding", label: "A Ask" },
              { value: "actionLearning", label: "B Learn" }
            ]}
            onChange={(userFit) => onChange({ ...config, userFit })}
          />
          <button
            type="button"
            onClick={() =>
              onChange({
                saveMode: "manual",
                labelMode: "priority",
                resultLayout: "tableFirst",
                itemDetail: "compact",
                reviewState: "simple",
                userFit: "onboarding"
              })
            }
            className="rounded-md border border-line px-3 py-2 text-xs font-semibold hover:bg-surface lg:col-span-2 xl:col-span-3"
          >
            Reset to all A baseline
          </button>
        </div>
      ) : null}
    </section>
  );
}

function SegmentedControl<T extends SaveModeVariant | LabelVariant | ResultLayoutVariant | ItemDetailVariant | ReviewStateVariant | UserFitVariant>({
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
