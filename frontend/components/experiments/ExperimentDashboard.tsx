"use client";

import Link from "next/link";
import { ArrowRight, FlaskConical } from "lucide-react";
import { useEffect, useState } from "react";
import { ExperimentSwitchPanel } from "@/components/analysis/ExperimentSwitchPanel";
import {
  ANALYSIS_EXPERIMENT_STORAGE_KEY,
  DEFAULT_ANALYSIS_EXPERIMENT,
  parseAnalysisExperiment,
  stringifyAnalysisExperiment,
  type AnalysisExperimentConfig
} from "@/lib/experiments";

const candidates = [
  {
    title: "1. Dictionary save",
    a: "Manual save",
    b: "Auto-save high priority",
    question: "Does automation reduce cleanup time, or create more junk to remove?"
  },
  {
    title: "2. Highlight labels",
    a: "Learning priority",
    b: "Reason shown",
    question: "Does the user decide faster with priority, or with explanation?"
  },
  {
    title: "3. Result layout",
    a: "Table first",
    b: "Reading context first",
    question: "Does cleanup work better as a list, or inside the source text?"
  },
  {
    title: "4. Item detail",
    a: "Compact item",
    b: "Learning card",
    question: "How much detail is useful before it becomes reading burden?"
  },
  {
    title: "5. Review state",
    a: "New / Viewed / Familiar",
    b: "Review soon / Mastered / Ignore",
    question: "Should review feel lightweight now, or study-ready from the start?"
  },
  {
    title: "6. User fit",
    a: "Ask during onboarding",
    b: "Learn from actions",
    question: "Should personalization start from settings, or observed behavior?"
  }
];

export function ExperimentDashboard() {
  const [config, setConfig] = useState<AnalysisExperimentConfig>(DEFAULT_ANALYSIS_EXPERIMENT);

  useEffect(() => {
    setConfig(parseAnalysisExperiment(window.localStorage.getItem(ANALYSIS_EXPERIMENT_STORAGE_KEY)));
  }, []);

  useEffect(() => {
    window.localStorage.setItem(ANALYSIS_EXPERIMENT_STORAGE_KEY, stringifyAnalysisExperiment(config));
  }, [config]);

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-line bg-panel p-6 shadow-material">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">Experiment dashboard</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-700">
              Switch all documented A/B candidates here, then open the demo result and collect team feedback on cleanup time,
              saved item quality, and reading flow.
            </p>
          </div>
          <Link href="/analysis/demo" className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white">
            Test demo result
            <ArrowRight size={16} />
          </Link>
        </div>
      </section>

      <ExperimentSwitchPanel config={config} onChange={setConfig} defaultOpen />

      <section className="grid gap-4 lg:grid-cols-2">
        {candidates.map((candidate) => (
          <article key={candidate.title} className="rounded-lg border border-line bg-panel p-5 shadow-material">
            <div className="flex items-start gap-3">
              <FlaskConical size={20} className="mt-0.5 text-accent" />
              <div>
                <h2 className="font-semibold">{candidate.title}</h2>
                <p className="mt-2 text-sm text-neutral-600">{candidate.question}</p>
                <div className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
                  <div className="rounded-md bg-surface p-3">
                    <p className="text-xs font-semibold uppercase text-neutral-500">A</p>
                    <p className="mt-1 font-medium">{candidate.a}</p>
                  </div>
                  <div className="rounded-md bg-surface p-3">
                    <p className="text-xs font-semibold uppercase text-neutral-500">B</p>
                    <p className="mt-1 font-medium">{candidate.b}</p>
                  </div>
                </div>
              </div>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
