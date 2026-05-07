"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AnalysisResult } from "@/lib/types";
import { DomainOverviewCard } from "./DomainOverviewCard";
import { LayeredSummaryPanel } from "./LayeredSummaryPanel";
import { SentenceDecompositionCard } from "./SentenceDecompositionCard";
import { TermTable } from "./TermTable";
import { AnalysisProgress } from "./AnalysisProgress";
import { ErrorState } from "../common/ErrorState";

export function AnalysisResultView({ documentId }: { documentId: string }) {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [step, setStep] = useState(1);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setInterval(() => {
      setElapsed((value) => value + 1);
      setStep((value) => Math.min(value + 1, 3));
    }, 1000);

    async function loadOrAnalyze() {
      try {
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

  if (error) return <ErrorState message={error} />;
  if (!analysis) return <AnalysisProgress step={step} elapsed={elapsed} />;

  return (
    <div className="space-y-6">
      <DomainOverviewCard analysis={analysis} />
      <LayeredSummaryPanel analysis={analysis} />
      <TermTable analysis={analysis} />
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Sentence structures</h2>
        {analysis.sentences.map((sentence) => <SentenceDecompositionCard key={sentence.core_structure} sentence={sentence} />)}
      </section>
    </div>
  );
}
