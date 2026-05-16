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
import { DocumentPageReader, SectionLessonCard, type SectionLessonSelection, type SectionPreparationStatus } from "./DocumentPageReader";
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
  const [sourceReady, setSourceReady] = useState(false);
  const [sectionLesson, setSectionLesson] = useState<SectionLessonSelection | null>(null);
  const [sectionPreparation, setSectionPreparation] = useState<SectionPreparationStatus | null>(null);
  const [stopSectionPreparation, setStopSectionPreparation] = useState(false);
  const [continueSectionPreparationKey, setContinueSectionPreparationKey] = useState(0);
  const [showDetailedOutput, setShowDetailedOutput] = useState(false);
  const [analysisMissing, setAnalysisMissing] = useState(false);

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
        let loadedDocument: DocumentRead | null = null;
        try {
          loadedDocument = await api.getDocument(documentId);
          if (!cancelled) setDocument(loadedDocument);
        } catch {
          if (!cancelled) setDocument(null);
        }
        if (loadedDocument && shouldOpenSectionWorkspaceWithoutBaseAnalysis(loadedDocument)) {
          if (!cancelled) {
            setAnalysisMissing(true);
            setStep(4);
          }
          return;
        }
        try {
          const existing = await api.getAnalysis(documentId);
          if (!cancelled) {
            setAnalysis(existing);
            setAnalysisMissing(false);
            setStep(4);
          }
          return;
        } catch {
          if (loadedDocument && shouldOpenSectionWorkspaceWithoutBaseAnalysis(loadedDocument)) {
            if (!cancelled) {
              setAnalysisMissing(true);
              setStep(4);
            }
            return;
          }
          if (!cancelled) setStep(2);
        }
        const created = await api.analyzeDocument(documentId);
        if (!cancelled) {
          setAnalysis(created);
          setAnalysisMissing(false);
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
  if (!analysis && analysisMissing && document) {
    const isVideoSource = document.source_type === "transcript" || document.source_type === "video_segment";
    const isDocumentSource = documentId !== DEMO_DOCUMENT_ID && !isVideoSource;
    const hasPdfViewer = Boolean(document.source_type === "pdf" && document.has_original_file);
    const workspaceContent = (
      <div className="min-w-0 space-y-6">
        {isDocumentSource ? (
          <SectionPreparationPanel
            status={sectionPreparation}
            onStop={() => setStopSectionPreparation(true)}
            onContinue={() => {
              setStopSectionPreparation(false);
              setContinueSectionPreparationKey((value) => value + 1);
            }}
          />
        ) : null}
        {isDocumentSource ? <PaperMapProgressPanel documentId={documentId} refreshKey={paperMapRefreshKey} /> : null}
        {isDocumentSource ? (
          <DocumentPageReader
            documentId={documentId}
            onSectionAnalyzed={() => setPaperMapRefreshKey((value) => value + 1)}
            onSectionLesson={setSectionLesson}
            onPreparationStatus={setSectionPreparation}
            stopPreparation={stopSectionPreparation}
            continuePreparationKey={continueSectionPreparationKey}
            onSourcePageChange={setRequestedPdfPage}
            requestedSourcePage={requestedPdfPage}
            sourceReady={!hasPdfViewer || sourceReady}
            hideInlineLesson
          />
        ) : null}
        {sectionLesson ? (
          <SectionLessonCard
            analysis={sectionLesson.analysis}
            sectionNumber={sectionLesson.sectionNumber}
            sectionLabel={sectionLesson.sectionLabel}
            isAnalyzingNext={false}
          />
        ) : null}
      </div>
    );
    return (
      <div className="space-y-6">
        {hasPdfViewer ? (
          <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.12fr)_minmax(0,0.88fr)]">
            <div className="min-w-0 xl:sticky xl:top-4">
              <PdfSourcePane document={document} requestedPage={requestedPdfPage} onPageChange={setRequestedPdfPage} onReady={() => setSourceReady(true)} />
            </div>
            <div className="min-w-0 xl:max-h-[calc(100vh-120px)] xl:overflow-y-auto xl:pr-1">{workspaceContent}</div>
          </div>
        ) : (
          workspaceContent
        )}
      </div>
    );
  }
  if (!analysis) return <AnalysisProgress step={step} elapsed={elapsed} />;

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
  const experimentControls = documentId === DEMO_DOCUMENT_ID ? (
    <>
      <ExperimentSwitchPanel config={config} onChange={setConfig} />
      {autoSaveStatus ? (
        <div className="rounded-lg border border-line bg-blue-50 px-4 py-3 text-sm font-medium text-accent">{autoSaveStatus}</div>
      ) : null}
    </>
  ) : null;
  const scopeNotice = isSectionLevel && isVideoSource ? (
    <section className="rounded-lg border border-line bg-panel p-4 text-sm leading-6 text-neutral-700 shadow-material">
      <p className="font-semibold text-ink">Transcript scope</p>
      <p className="mt-1">
        This result covers the transcript text sent from the video page. Longer videos should be analyzed scene by scene, then merged into a full-video learning guide.
      </p>
    </section>
  ) : null;
  const guideContent = (
    <div className="min-w-0 space-y-6">
      {isDocumentSource ? (
        <SectionPreparationPanel
          status={sectionPreparation}
          onStop={() => setStopSectionPreparation(true)}
          onContinue={() => {
            setStopSectionPreparation(false);
            setContinueSectionPreparationKey((value) => value + 1);
          }}
        />
      ) : null}
      {isDocumentSource ? <PaperMapProgressPanel documentId={documentId} refreshKey={paperMapRefreshKey} /> : null}
      {isDocumentSource ? (
        <DocumentPageReader
          documentId={documentId}
          onSectionAnalyzed={() => setPaperMapRefreshKey((value) => value + 1)}
          onSectionLesson={setSectionLesson}
          onPreparationStatus={setSectionPreparation}
          stopPreparation={stopSectionPreparation}
          continuePreparationKey={continueSectionPreparationKey}
          onSourcePageChange={setRequestedPdfPage}
          requestedSourcePage={requestedPdfPage}
          sourceReady={!hasPdfViewer || sourceReady}
          hideInlineLesson
        />
      ) : null}
      {sectionLesson ? (
        <SectionLessonCard
          analysis={sectionLesson.analysis}
          sectionNumber={sectionLesson.sectionNumber}
          sectionLabel={sectionLesson.sectionLabel}
          isAnalyzingNext={false}
        />
      ) : null}
      {isVideoSource ? (
        <>
          <ConceptMapPanel analysis={analysis} sourceKind="video" />
          {learningObjects}
          {summaries}
          {sentenceStructures}
        </>
      ) : null}
      {!isVideoSource ? (
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
      ) : null}
      {showDetailedOutput && !isVideoSource ? (
        <>
          {documentId !== DEMO_DOCUMENT_ID ? (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={async () => {
                  setRerunning(true);
                  try {
                    const created = await api.analyzeDocument(documentId);
                    setAnalysis(created);
                  } finally {
                    setRerunning(false);
                  }
                }}
                disabled={rerunning}
                className="rounded-md border border-line bg-panel px-3 py-2 text-xs font-semibold text-ink shadow-material hover:bg-surface disabled:text-neutral-500"
              >
                {rerunning ? "Rebuilding..." : "Rebuild base analysis"}
              </button>
            </div>
          ) : null}
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
      <DomainOverviewCard analysis={analysis} />
      {hasPdfViewer && document ? (
        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.12fr)_minmax(0,0.88fr)]">
          <div className="min-w-0 xl:sticky xl:top-4">
            <PdfSourcePane document={document} requestedPage={requestedPdfPage} onPageChange={setRequestedPdfPage} onReady={() => setSourceReady(true)} />
          </div>
          <div className="min-w-0 xl:max-h-[calc(100vh-120px)] xl:overflow-y-auto xl:pr-1">{guideContent}</div>
        </div>
      ) : (
        guideContent
      )}
      {scopeNotice || experimentControls ? (
        <div className="space-y-4">
          {scopeNotice}
          {experimentControls}
        </div>
      ) : null}
    </div>
  );
}

function shouldOpenSectionWorkspaceWithoutBaseAnalysis(document: DocumentRead) {
  if (document.source_type === "pdf") return true;
  return document.content.length > 5000;
}

function SectionPreparationPanel({
  status,
  onStop,
  onContinue
}: {
  status: SectionPreparationStatus | null;
  onStop: () => void;
  onContinue: () => void;
}) {
  if (!status) return null;
  const progress = status.total ? Math.min(100, Math.round((status.ready / status.total) * 100)) : 0;
  const canContinue = !status.running && status.ready < status.total;
  return (
    <section className="rounded-lg border border-blue-200 bg-blue-50 p-4 shadow-material">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent">Section preparation</p>
          <h2 className="mt-1 text-lg font-semibold text-ink">{status.message}</h2>
          <p className="mt-1 text-sm font-medium text-neutral-700">
            {status.ready} / {status.total} ready · Mode: {status.mode}
            {status.running ? ", currently running" : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2 text-sm font-semibold text-accent">
            {status.running ? <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-accent" /> : null}
            {status.running ? "Analyzing" : status.ready >= status.total ? "Complete" : "Paused"}
          </div>
          {status.running ? (
            <button
              type="button"
              onClick={onStop}
              className="rounded-md border border-blue-200 bg-white px-3 py-2 text-xs font-semibold text-ink hover:bg-blue-100"
            >
              Stop after current section
            </button>
          ) : canContinue ? (
            <button
              type="button"
              onClick={onContinue}
              className="rounded-md bg-accent px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700"
            >
              Continue preparation
            </button>
          ) : null}
        </div>
      </div>
      <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-white">
        <div className="h-full rounded-full bg-accent transition-all duration-500" style={{ width: `${progress}%` }} />
      </div>
    </section>
  );
}
