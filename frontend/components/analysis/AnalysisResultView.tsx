"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AnalysisResult, DocumentRead } from "@/lib/types";
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
import { ConceptMapPanel } from "./ConceptMapPanel";
import { DocumentPageReader, SectionLessonCard } from "./DocumentPageReader";
import { ExperimentSwitchPanel } from "./ExperimentSwitchPanel";
import { PaperMapProgressPanel } from "./PaperMapProgressPanel";
import { PdfSourcePane } from "./PdfSourcePane";
import { ErrorState } from "../common/ErrorState";

export function AnalysisResultView({ documentId }: { documentId: string }) {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [document, setDocument] = useState<DocumentRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [step, setStep] = useState(1);
  const [config, setConfig] = useState<AnalysisExperimentConfig>(DEFAULT_ANALYSIS_EXPERIMENT);
  const [autoSaveStatus, setAutoSaveStatus] = useState<string | null>(null);
  const [rerunning, setRerunning] = useState(false);
  const [paperMapRefreshKey, setPaperMapRefreshKey] = useState(0);
  const [requestedPdfPage, setRequestedPdfPage] = useState<number | null>(null);
  const [sectionLesson, setSectionLesson] = useState<{ analysis: AnalysisResult; sectionNumber: number } | null>(null);
  const [showDetailedOutput, setShowDetailedOutput] = useState(false);

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
          const loadedDocument = await api.getDocument(documentId);
          if (!cancelled) setDocument(loadedDocument);
        } catch {
          if (!cancelled) setDocument(null);
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
      } catch (err) {
        const message = err instanceof Error ? err.message : "Could not analyze this document. Check backend logs and selected model preset.";
        if (!cancelled) setError(message);
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

  async function rerunAnalysis() {
    setRerunning(true);
    setError(null);
    setStep(2);
    try {
      const created = await api.analyzeDocument(documentId);
      setAnalysis(created);
      setStep(4);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not re-analyze this document.");
    } finally {
      setRerunning(false);
    }
  }

  const learningObjects = <TermTable analysis={analysis} config={config} />;
  const summaries = <LayeredSummaryPanel analysis={analysis} />;
  const reader = <ReadingContextPanel analysis={analysis} />;
  const sentenceStructures = (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold">Sentence structures</h2>
      {analysis.sentences.map((sentence) => <SentenceDecompositionCard key={sentence.core_structure} sentence={sentence} />)}
    </section>
  );
  const isSectionLevel = analysis.quality_warnings?.some((warning) => warning.includes("section-level analysis"));
  const isVideoSource = document?.source_type === "transcript" || document?.source_type === "video_segment";
  const isDocumentSource = documentId !== DEMO_DOCUMENT_ID && !isVideoSource;
  const hasPdfViewer = Boolean(document?.source_type === "pdf" && document.has_original_file);
  const experimentControls = (
    <>
      <ExperimentSwitchPanel config={config} onChange={setConfig} />
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
    </>
  );
  const scopeNotice = isSectionLevel ? (
    <section className="rounded-lg border border-line bg-panel p-4 text-sm leading-6 text-neutral-700 shadow-material">
      <p className="font-semibold text-ink">{isVideoSource ? "Transcript scope" : "Scope"}</p>
      <p className="mt-1">
        {isVideoSource
          ? "This result covers the transcript text sent from the video page. Longer videos should be analyzed scene by scene, then merged into a full-video learning guide."
          : "This base result covers the first readable section. Use Section study and Auto-study to analyze more sections; the paper map and whole-paper draft update from analyzed section caches."}
      </p>
    </section>
  ) : null;
  const guideContent = (
    <div className="min-w-0 space-y-6">
      {isDocumentSource ? (
        <DocumentPageReader
          documentId={documentId}
          onSectionAnalyzed={() => setPaperMapRefreshKey((value) => value + 1)}
          onSectionLesson={setSectionLesson}
          onSourcePageChange={setRequestedPdfPage}
          requestedSourcePage={requestedPdfPage}
          hideInlineLesson
        />
      ) : null}
      {sectionLesson ? <SectionLessonCard analysis={sectionLesson.analysis} sectionNumber={sectionLesson.sectionNumber} isAnalyzingNext={false} /> : null}
      {isDocumentSource ? <PaperMapProgressPanel documentId={documentId} refreshKey={paperMapRefreshKey} /> : null}
      <section className="rounded-lg border border-line bg-panel shadow-material">
        <button
          type="button"
          onClick={() => setShowDetailedOutput((value) => !value)}
          className="flex w-full items-center justify-between gap-3 p-4 text-left"
        >
          <span>
            <span className="block text-sm font-semibold text-ink">Detailed generated output</span>
            <span className="mt-1 block text-xs leading-5 text-neutral-600">
              Open for the full model output: concept cards, learning-object table, layered summaries, and sentence structures.
            </span>
          </span>
          {showDetailedOutput ? <ChevronDown size={18} className="shrink-0 text-neutral-500" /> : <ChevronRight size={18} className="shrink-0 text-neutral-500" />}
        </button>
      </section>
      {showDetailedOutput ? (
        <>
          <ConceptMapPanel analysis={analysis} sourceKind={isVideoSource ? "video" : "document"} />
          {config.resultLayout === "readingContextFirst" ? reader : null}
          {learningObjects}
          {summaries}
          {sentenceStructures}
        </>
      ) : null}
    </div>
  );

  return (
    <div className="space-y-6">
      {documentId === DEMO_DOCUMENT_ID ? (
        <div className="rounded-lg border border-line bg-blue-50 p-4 text-sm text-accent">
          Demo mode uses fixed sample data so Vercel reviewers can test UI and A/B variants without a local model server.
        </div>
      ) : null}
      {documentId !== DEMO_DOCUMENT_ID ? (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={rerunAnalysis}
            disabled={rerunning}
            className="rounded-md border border-line bg-panel px-4 py-2 text-sm font-semibold text-ink shadow-material hover:bg-surface disabled:text-neutral-500"
          >
            {rerunning ? "Re-analyzing..." : "Re-analyze with current model"}
          </button>
        </div>
      ) : null}
      <DomainOverviewCard analysis={analysis} />
      {hasPdfViewer && document ? (
        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.12fr)_minmax(0,0.88fr)]">
          <div className="min-w-0 xl:sticky xl:top-4">
            <PdfSourcePane document={document} requestedPage={requestedPdfPage} onPageChange={setRequestedPdfPage} />
          </div>
          {guideContent}
        </div>
      ) : (
        guideContent
      )}
      <div className="space-y-4">
        {scopeNotice}
        {experimentControls}
      </div>
    </div>
  );
}
