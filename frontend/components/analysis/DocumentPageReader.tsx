"use client";

import { CheckCircle2, ChevronLeft, ChevronRight, Eye, EyeOff, Paperclip, ScanText, SkipForward } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { AnalysisResult, DocumentRead, DocumentSection } from "@/lib/types";

export function DocumentPageReader({
  documentId,
  onSectionAnalyzed,
  onSectionLesson,
  onSourcePageChange,
  requestedSourcePage,
  hideInlineLesson = false
}: {
  documentId: string;
  onSectionAnalyzed?: () => void;
  onSectionLesson?: (lesson: { analysis: AnalysisResult; sectionNumber: number }) => void;
  onSourcePageChange?: (page: number | null) => void;
  requestedSourcePage?: number | null;
  hideInlineLesson?: boolean;
}) {
  const [document, setDocument] = useState<DocumentRead | null>(null);
  const [sections, setSections] = useState<DocumentSection[]>([]);
  const [pageIndex, setPageIndex] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isBatchAnalyzing, setIsBatchAnalyzing] = useState(false);
  const [batchStatus, setBatchStatus] = useState("");
  const [isAttaching, setIsAttaching] = useState(false);
  const [sectionAnalysis, setSectionAnalysis] = useState<AnalysisResult | null>(null);
  const [sectionAnalysisIndex, setSectionAnalysisIndex] = useState<number | null>(null);
  const [error, setError] = useState("");
  const attachInputRef = useRef<HTMLInputElement>(null);
  const currentSection = sections[pageIndex];
  const page = currentSection?.text ?? "";
  const analyzedCount = sections.filter((section) => section.analyzed).length;
  const nextUnanalyzedIndex = sections.findIndex((section, index) => index > pageIndex && !section.analyzed);
  const fallbackUnanalyzedIndex = sections.findIndex((section) => !section.analyzed);
  const targetUnanalyzedIndex = nextUnanalyzedIndex >= 0 ? nextUnanalyzedIndex : fallbackUnanalyzedIndex;
  const plannedBatchIndices = nextUnanalyzedSectionIndices(sections, pageIndex, 3);
  const progressStorageKey = `gemmalens:auto-study:${documentId}`;

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.getDocument(documentId), api.listDocumentSections(documentId)])
      .then(([loaded, loadedSections]) => {
        if (!cancelled) {
          setDocument(loaded);
          setSections(loadedSections);
        }
      })
      .catch(() => {
        if (!cancelled) setError("Could not load the source document reader.");
      });
    return () => {
      cancelled = true;
    };
  }, [documentId]);

  useEffect(() => {
    setSectionAnalysis(null);
    setSectionAnalysisIndex(null);
    setError("");
  }, [pageIndex]);

  useEffect(() => {
    let cancelled = false;
    if (!document || !currentSection?.analyzed || sectionAnalysisIndex === currentSection.index) return;
    api
      .getDocumentSectionAnalysis(document.id, currentSection.index)
      .then((cached) => {
        if (cancelled) return;
        setSectionAnalysis(cached);
        setSectionAnalysisIndex(currentSection.index);
        onSectionLesson?.({ analysis: cached, sectionNumber: pageIndex + 1 });
      })
      .catch(() => {
        if (!cancelled) {
          setSectionAnalysis(null);
          setSectionAnalysisIndex(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [currentSection?.analyzed, currentSection?.index, document, onSectionLesson, pageIndex, sectionAnalysisIndex]);

  useEffect(() => {
    onSourcePageChange?.(pdfPageFromLabel(currentSection?.source_label ?? null));
  }, [currentSection?.source_label, onSourcePageChange]);

  useEffect(() => {
    if (!requestedSourcePage || !sections.length) return;
    const currentPage = pdfPageFromLabel(currentSection?.source_label ?? null);
    if (currentPage === requestedSourcePage) return;
    const matchingIndex = sections.findIndex((section) => pdfPageFromLabel(section.source_label) === requestedSourcePage);
    if (matchingIndex >= 0) setPageIndex(matchingIndex);
  }, [currentSection?.source_label, requestedSourcePage, sections]);

  useEffect(() => {
    const saved = readAutoStudyProgress(progressStorageKey);
    if (saved && !batchStatus) {
      setBatchStatus(saved.status);
    }
  }, [batchStatus, progressStorageKey]);

  async function analyzeSectionAt(index: number, options: { keepBusy?: boolean } = {}) {
    const section = sections[index];
    if (!document || !section || !section.text.trim()) return;
    setPageIndex(index);
    setIsAnalyzing(true);
    setError("");
    try {
      const created = await api.analyzeDocumentSection(document.id, section.index);
      setSectionAnalysis(created);
      setSectionAnalysisIndex(section.index);
      onSectionLesson?.({ analysis: created, sectionNumber: index + 1 });
      setSections((current) =>
        current.map((currentSection) => (currentSection.index === section.index ? { ...currentSection, analyzed: true } : currentSection))
      );
      onSectionAnalyzed?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not analyze this section.");
      throw err;
    } finally {
      if (!options.keepBusy) setIsAnalyzing(false);
    }
  }

  async function analyzePage() {
    await analyzeSectionAt(pageIndex);
  }

  async function attachSourceFile(file: File) {
    if (!document) return;
    setIsAttaching(true);
    setError("");
    try {
      const updated = await api.attachDocumentFile(document.id, file);
      setDocument(updated);
      window.location.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not attach source file.");
    } finally {
      setIsAttaching(false);
    }
  }

  if (!document) {
    return (
      <section className="rounded-lg border border-line bg-panel p-5 text-sm text-neutral-600 shadow-material">
        {error || "Loading source reader..."}
      </section>
    );
  }
  if (document.source_type === "transcript" || document.source_type === "video_segment") return null;

  function goToNextUnanalyzed() {
    if (targetUnanalyzedIndex >= 0) setPageIndex(targetUnanalyzedIndex);
  }

  async function autoStudyNextSections() {
    if (!plannedBatchIndices.length || isBatchAnalyzing) return;
    setIsBatchAnalyzing(true);
    setIsAnalyzing(true);
    setBatchStatus("");
    const plannedCount = plannedBatchIndices.length;
    writeAutoStudyProgress(progressStorageKey, {
      status: `Starting server-side auto-study for ${plannedCount} sections...`,
      completed: 0,
      planned: plannedCount,
      updatedAt: Date.now()
    });
    try {
      const runningStatus = `Server is analyzing ${plannedCount} section(s). This can take time on local models.`;
      setBatchStatus(runningStatus);
      writeAutoStudyProgress(progressStorageKey, {
        status: runningStatus,
        completed: 0,
        planned: plannedCount,
        updatedAt: Date.now()
      });
      const result = await api.stagedAnalyzeDocument(documentId, { max_sections: plannedCount });
      const updatedSections = await api.listDocumentSections(documentId);
      setSections(updatedSections);
      const lastAnalyzed = result.analyzed_sections.at(-1);
      if (lastAnalyzed) setPageIndex(Math.max(0, lastAnalyzed - 1));
      onSectionAnalyzed?.();
      const status =
        result.status === "nothing_to_do"
          ? "All available sections are already analyzed."
          : `Finished ${result.analyzed_sections.length} section(s). Paper map updated.`;
      setBatchStatus(status);
      writeAutoStudyProgress(progressStorageKey, {
        status,
        completed: result.analyzed_sections.length,
        planned: plannedCount,
        updatedAt: Date.now()
      });
    } catch {
      const status = "Auto-study stopped. The last section needs attention. Use Auto-study next 3 to continue.";
      setBatchStatus(status);
      writeAutoStudyProgress(progressStorageKey, {
        status,
        completed: sections.filter((section) => section.analyzed).length,
        planned: plannedCount,
        updatedAt: Date.now()
      });
    } finally {
      setIsBatchAnalyzing(false);
      setIsAnalyzing(false);
    }
  }

  return (
    <section className="rounded-lg border border-line bg-panel shadow-material">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line p-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Section study</p>
          <h2 className="mt-1 text-lg font-semibold">Move through extracted sections</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-neutral-600">
            Use this when the whole document is too long for one edge-model pass. These are model-input text sections, not rendered PDF pages.
          </p>
          <p className="mt-2 text-xs font-semibold text-neutral-600">
            {analyzedCount} / {sections.length || 1} sections analyzed
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <button
            type="button"
            onClick={goToNextUnanalyzed}
            disabled={targetUnanalyzedIndex < 0 || isBatchAnalyzing}
            className="inline-flex items-center gap-2 rounded-md border border-line px-4 py-2 text-sm font-semibold text-ink hover:bg-surface disabled:opacity-40"
          >
            <SkipForward size={16} />
            Next unstudied
          </button>
          <button
            type="button"
            onClick={autoStudyNextSections}
            disabled={!plannedBatchIndices.length || isBatchAnalyzing || isAnalyzing}
            className="inline-flex items-center gap-2 rounded-md border border-line bg-panel px-4 py-2 text-sm font-semibold text-ink hover:bg-surface disabled:opacity-40"
          >
            <ScanText size={16} />
            {isBatchAnalyzing ? "Auto-studying..." : "Auto-study next 3"}
          </button>
          {document.source_type === "pdf" && !document.has_original_file ? (
            <>
              <button
                type="button"
                onClick={() => attachInputRef.current?.click()}
                disabled={isAttaching}
                className="inline-flex items-center gap-2 rounded-md border border-line px-4 py-2 text-sm font-semibold text-ink hover:bg-surface disabled:opacity-50"
              >
                <Paperclip size={16} />
                {isAttaching ? "Attaching..." : "Attach original PDF"}
              </button>
              <input
                ref={attachInputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="sr-only"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) attachSourceFile(file);
                  event.target.value = "";
                }}
              />
            </>
          ) : null}
          <button
            type="button"
            onClick={analyzePage}
            disabled={isAnalyzing || isBatchAnalyzing || !currentSection || !page.trim()}
            className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:bg-neutral-300 disabled:text-neutral-600"
          >
            <ScanText size={16} />
            {isAnalyzing ? "Analyzing section..." : currentSection?.analyzed ? "Re-analyze section" : "Analyze this section"}
          </button>
        </div>
      </div>
      {batchStatus ? (
        <div className="border-b border-line bg-blue-50 px-5 py-3 text-sm font-medium text-accent">{batchStatus}</div>
      ) : null}
      {sections.length ? (
        <div className="flex gap-1 overflow-x-auto border-b border-line px-5 py-2">
          {sections.map((section, index) => (
            <button
              key={section.index}
              type="button"
              onClick={() => setPageIndex(index)}
              className={`flex h-8 min-w-10 items-center justify-center rounded-md border px-2 text-[11px] font-semibold ${
                index === pageIndex
                  ? "border-accent bg-accent text-white"
                  : section.analyzed
                    ? "border-green-200 bg-green-50 text-green-700"
                    : "border-line bg-panel text-neutral-500 hover:bg-surface"
              }`}
              title={`Section ${section.section_number}${section.analyzed ? " analyzed" : " not analyzed"}`}
            >
              {section.analyzed && index !== pageIndex ? <CheckCircle2 size={13} /> : `S${section.section_number}`}
            </button>
          ))}
        </div>
      ) : null}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-3">
        <button
          type="button"
          onClick={() => setPageIndex((value) => Math.max(0, value - 1))}
          disabled={pageIndex === 0}
          className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-xs font-semibold text-ink hover:bg-surface disabled:opacity-40"
        >
          <ChevronLeft size={15} />
          Previous
        </button>
        <div className="text-center">
          <p className="text-sm font-semibold text-ink">
            Section {currentSection?.section_number ?? pageIndex + 1} / {currentSection?.total_sections ?? Math.max(sections.length, 1)}
          </p>
          {currentSection?.source_label ? <p className="text-xs font-semibold text-neutral-600">{currentSection.source_label}</p> : null}
          <p className="text-xs text-neutral-500">{(currentSection?.char_count ?? page.length).toLocaleString()} chars from backend-cleaned text</p>
          {currentSection?.analyzed ? <p className="text-xs font-semibold text-green-700">Analyzed</p> : null}
        </div>
        <button
          type="button"
          onClick={() => setPageIndex((value) => Math.min(sections.length - 1, value + 1))}
          disabled={!sections.length || pageIndex >= sections.length - 1}
          className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-xs font-semibold text-ink hover:bg-surface disabled:opacity-40"
        >
          Next
          <ChevronRight size={15} />
        </button>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface px-5 py-3">
        <div className="max-w-2xl space-y-1">
          {currentSection?.preview ? <p className="text-sm font-medium leading-6 text-ink">{currentSection.preview}</p> : null}
          <p className="text-xs leading-5 text-neutral-600">
            The left PDF is the visual source. This section text is what the model can read; it may lose equations, columns, or line breaks.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          className="inline-flex items-center gap-2 rounded-md border border-line bg-panel px-3 py-2 text-xs font-semibold text-ink hover:bg-white"
        >
          {expanded ? <EyeOff size={15} /> : <Eye size={15} />}
          {expanded ? "Hide source text" : "Show source text"}
        </button>
      </div>
      {expanded ? (
        <>
          {error ? <p className="mx-5 mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
          <article className="max-h-[420px] overflow-y-auto whitespace-pre-wrap p-5 text-sm leading-7 text-neutral-800">{page}</article>
        </>
      ) : error ? (
        <p className="mx-5 my-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      ) : null}
      {sectionAnalysis && !hideInlineLesson ? (
        <SectionLessonCard
          analysis={sectionAnalysis}
          sectionNumber={pageIndex + 1}
          onAnalyzeNext={targetUnanalyzedIndex >= 0 ? () => analyzeSectionAt(targetUnanalyzedIndex) : undefined}
          isAnalyzingNext={isAnalyzing}
        />
      ) : null}
    </section>
  );
}

export function SectionLessonCard({
  analysis,
  sectionNumber,
  onAnalyzeNext,
  isAnalyzingNext
}: {
  analysis: AnalysisResult;
  sectionNumber: number;
  onAnalyzeNext?: () => void;
  isAnalyzingNext: boolean;
}) {
  const terms = analysis.terms.slice(0, 6);
  const phrases = analysis.phrases.slice(0, 6);
  return (
    <div className="border-t border-line p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Section {sectionNumber} lesson</p>
      <h3 className="mt-1 text-lg font-semibold">{analysis.summaries.one_line}</h3>
      <p className="mt-2 text-sm leading-6 text-neutral-700">{analysis.summaries.simple}</p>
      {analysis.concepts?.length ? (
        <div className="mt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Concept anchors</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {analysis.concepts.slice(0, 5).map((concept) => (
              <span key={concept.concept} className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-accent">
                {concept.concept}
              </span>
            ))}
          </div>
        </div>
      ) : null}
      <div className="mt-5 grid gap-4">
        <MiniList title="Terms to notice" rows={terms.map((term) => [term.term, term.meaning])} />
        <MiniList title="Academic expressions" rows={phrases.map((phrase) => [phrase.phrase, phrase.explanation])} />
      </div>
      {analysis.sentences[0] ? (
        <div className="mt-5 rounded-md border border-line bg-surface p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Hard sentence pattern</p>
          <p className="mt-2 text-sm font-semibold text-ink">{analysis.sentences[0].core_structure}</p>
          <p className="mt-2 text-sm leading-6 text-neutral-700">{analysis.sentences[0].korean_explanation}</p>
        </div>
      ) : null}
      {onAnalyzeNext ? (
        <div className="mt-5 flex justify-end border-t border-line pt-4">
          <button
            type="button"
            onClick={onAnalyzeNext}
            disabled={isAnalyzingNext}
            className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:bg-neutral-300 disabled:text-neutral-600"
          >
            <SkipForward size={16} />
            {isAnalyzingNext ? "Analyzing next section..." : "Analyze next unstudied"}
          </button>
        </div>
      ) : null}
    </div>
  );
}

function MiniList({ title, rows }: { title: string; rows: Array<[string, string]> }) {
  return (
    <div className="rounded-md border border-line bg-surface p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{title}</p>
      {rows.length ? (
        <div className="mt-3 space-y-3">
          {rows.map(([label, description]) => (
            <div key={label}>
              <p className="text-sm font-semibold text-ink">{label}</p>
              <p className="mt-1 text-xs leading-5 text-neutral-600">{description}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm text-neutral-600">No strong items found for this section.</p>
      )}
    </div>
  );
}

function pdfPageFromLabel(label: string | null) {
  const match = label?.match(/^PDF page (\d+)$/);
  return match ? Number(match[1]) : null;
}

function nextUnanalyzedSectionIndices(sections: DocumentSection[], currentIndex: number, limit: number) {
  const afterCurrent = sections
    .map((section, index) => ({ section, index }))
    .filter(({ section, index }) => index >= currentIndex && !section.analyzed)
    .map(({ index }) => index);
  const beforeCurrent = sections
    .map((section, index) => ({ section, index }))
    .filter(({ section, index }) => index < currentIndex && !section.analyzed)
    .map(({ index }) => index);
  return [...afterCurrent, ...beforeCurrent].slice(0, limit);
}

type AutoStudyProgress = {
  status: string;
  completed: number;
  planned: number;
  updatedAt: number;
};

function readAutoStudyProgress(key: string): AutoStudyProgress | null {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AutoStudyProgress;
    if (!parsed.status || !parsed.updatedAt) return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeAutoStudyProgress(key: string, progress: AutoStudyProgress) {
  try {
    window.localStorage.setItem(key, JSON.stringify(progress));
  } catch {
    // Ignore storage failures; auto-study still works for the current session.
  }
}
