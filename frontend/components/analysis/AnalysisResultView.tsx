"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AnalysisResult } from "@/lib/types";
import { demoModeEnabled } from "@/lib/demoMode";
import { demoAnalysis, DEMO_DOCUMENT_ID } from "@/lib/demoData";
import {
  ANALYSIS_EXPERIMENT_STORAGE_KEY,
  DEFAULT_ANALYSIS_EXPERIMENT,
  parseAnalysisExperiment,
  stringifyAnalysisExperiment,
  type AnalysisExperimentConfig
} from "@/lib/experiments";
import { DomainOverviewCard } from "./DomainOverviewCard";
import { LayeredSummaryPanel } from "./LayeredSummaryPanel";
import { ReadingContextPanel } from "./ReadingContextPanel";
import { SentenceDecompositionCard } from "./SentenceDecompositionCard";
import { buildRows, TermTable } from "./TermTable";
import { AnalysisProgress } from "./AnalysisProgress";
import { ExperimentSwitchPanel } from "./ExperimentSwitchPanel";
import { ErrorState } from "../common/ErrorState";

export function AnalysisResultView({ documentId }: { documentId: string }) {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [step, setStep] = useState(1);
  const [config, setConfig] = useState<AnalysisExperimentConfig>(DEFAULT_ANALYSIS_EXPERIMENT);
  const [autoSaveStatus, setAutoSaveStatus] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setInterval(() => {
      setElapsed((value) => value + 1);
      setStep((value) => Math.min(value + 1, 3));
    }, 1000);

    async function loadOrAnalyze() {
      try {
        if (documentId === DEMO_DOCUMENT_ID) {
          if (!demoModeEnabled) {
            setError("Demo result is disabled in local real-model mode.");
            return;
          }
          if (!cancelled) {
            setAnalysis(demoAnalysis);
            setStep(4);
          }
          return;
        }
        try {
          const existing = await api.getAnalysis(documentId);
          if (!cancelled) {
            setAnalysis(existing);
            setStep(4);
          }
          return;
        } catch {
          if (!cancelled) setStep(2);
        }
        const created = await api.analyzeDocument(documentId);
        if (!cancelled) {
          setAnalysis(created);
          setStep(4);
        }
      } catch {
        if (!cancelled) setError("Could not analyze this document. Check backend logs and selected model preset.");
      } finally {
        window.clearInterval(timer);
      }
    }

    loadOrAnalyze();
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [documentId]);

  useEffect(() => {
    setConfig(parseAnalysisExperiment(window.localStorage.getItem(ANALYSIS_EXPERIMENT_STORAGE_KEY)));
  }, []);

  useEffect(() => {
    window.localStorage.setItem(ANALYSIS_EXPERIMENT_STORAGE_KEY, stringifyAnalysisExperiment(config));
  }, [config]);

  useEffect(() => {
    if (!analysis || config.saveMode !== "autoHighPriority") {
      setAutoSaveStatus(null);
      return;
    }

    const currentAnalysis = analysis;
    let cancelled = false;
    async function autoSaveHighPriority() {
      const rows = buildRows(currentAnalysis).filter((row) => row.highPriority);
      setAutoSaveStatus(`Auto-saving ${rows.length} high-priority items...`);
      await Promise.all(
        rows.map((row) =>
          currentAnalysis.document_id === DEMO_DOCUMENT_ID
            ? Promise.resolve()
            : api.saveDictionaryItem({
                item_type: row.type,
                text: row.text,
                meaning: row.meaning,
                source_sentence: row.source_sentence,
                document_id: currentAnalysis.document_id
              })
        )
      );
      if (!cancelled) setAutoSaveStatus(`${rows.length} high-priority items saved for B comparison.`);
    }

    autoSaveHighPriority().catch(() => {
      if (!cancelled) setAutoSaveStatus("Auto-save failed. Manual save is still available.");
    });

    return () => {
      cancelled = true;
    };
  }, [analysis, config.saveMode]);

  if (error) return <ErrorState message={error} />;
  if (!analysis) return <AnalysisProgress step={step} elapsed={elapsed} />;

  const learningObjects = <TermTable analysis={analysis} config={config} />;
  const summaries = <LayeredSummaryPanel analysis={analysis} />;
  const reader = <ReadingContextPanel analysis={analysis} />;
  const isSectionLevel = analysis.quality_warnings?.some((warning) => warning.includes("section-level analysis"));

  return (
    <div className="space-y-6">
      {documentId === DEMO_DOCUMENT_ID ? (
        <div className="rounded-lg border border-line bg-blue-50 p-4 text-sm text-accent">
          Demo mode uses fixed sample data so Vercel reviewers can test UI and A/B variants without a local model server.
        </div>
      ) : null}
      <ExperimentSwitchPanel config={config} onChange={setConfig} defaultOpen />
      <section className="rounded-lg border border-line bg-panel p-4 shadow-material">
        <p className="text-sm font-semibold">User-fit mode</p>
        <p className="mt-1 text-sm text-neutral-600">
          {config.userFit === "onboarding"
            ? "A Ask mode: analysis assumes level, support language, learning language, and field are selected before reading."
            : "B Learn mode: analysis should adapt from saved, ignored, viewed, and familiar items over time."}
        </p>
      </section>
      {autoSaveStatus ? (
        <div className="rounded-lg border border-line bg-blue-50 px-4 py-3 text-sm font-medium text-accent">{autoSaveStatus}</div>
      ) : null}
      {isSectionLevel ? (
        <section className="rounded-lg border border-line bg-panel p-4 text-sm leading-6 text-neutral-700 shadow-material">
          <p className="font-semibold text-ink">Scope</p>
          <p className="mt-1">
            This result covers the first readable section only. Full-paper staged analysis is planned so each section can be analyzed and then merged into a whole-paper view.
          </p>
        </section>
      ) : null}
      <DomainOverviewCard analysis={analysis} />
      {config.resultLayout === "tableFirst" ? (
        <>
          {learningObjects}
          {summaries}
        </>
      ) : (
        <>
          {reader}
          {learningObjects}
          {summaries}
        </>
      )}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Sentence structures</h2>
        {analysis.sentences.map((sentence) => <SentenceDecompositionCard key={sentence.core_structure} sentence={sentence} />)}
      </section>
    </div>
  );
}
