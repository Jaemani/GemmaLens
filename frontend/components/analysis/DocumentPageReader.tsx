"use client";

import { BookmarkPlus, CheckCircle2, ChevronLeft, ChevronRight, Eye, EyeOff, Paperclip, ScanText } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { AnalysisResult, DocumentRead, DocumentSection } from "@/lib/types";

export function DocumentPageReader({
  documentId,
  onSectionAnalyzed,
  onSectionLesson,
  onPreparationStatus,
  stopPreparation = false,
  continuePreparationKey = 0,
  onSourcePageChange,
  requestedSourcePage,
  sourceReady = true,
  hideInlineLesson = false
}: {
  documentId: string;
  onSectionAnalyzed?: () => void;
  onSectionLesson?: (lesson: SectionLessonSelection | null) => void;
  onPreparationStatus?: (status: SectionPreparationStatus | null) => void;
  stopPreparation?: boolean;
  continuePreparationKey?: number;
  onSourcePageChange?: (page: number | null) => void;
  requestedSourcePage?: number | null;
  sourceReady?: boolean;
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
  const [autoAnalyzeAll, setAutoAnalyzeAll] = useState(false);
  const [sectionAnalysis, setSectionAnalysis] = useState<AnalysisResult | null>(null);
  const [sectionAnalysisIndex, setSectionAnalysisIndex] = useState<number | null>(null);
  const [error, setError] = useState("");
  const attachInputRef = useRef<HTMLInputElement>(null);
  const sectionDrivenPdfPageRef = useRef<number | null>(null);
  const autoAnalyzeStartedRef = useRef(false);
  const stopPreparationRef = useRef(false);
  const currentPageGroupRef = useRef<HTMLDivElement | null>(null);
  const currentSection = sections[pageIndex];
  const page = currentSection?.text ?? "";
  const analyzedCount = sections.filter((section) => section.analyzed).length;
  const allSectionsAnalyzed = Boolean(sections.length && analyzedCount >= sections.length);
  const progressStorageKey = `gemmalens:auto-study:${documentId}`;
  const sectionGroups = groupSectionsByPdfPage(sections);
  const currentPdfPage = pdfPageFromLabel(currentSection?.source_label ?? null);
  const currentPageSectionNumber = currentSection ? sectionNumberWithinPdfPage(sections, pageIndex) : null;

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.getDocument(documentId), api.listDocumentSections(documentId), api.getProfile().catch(() => null)])
      .then(([loaded, loadedSections, profile]) => {
        if (!cancelled) {
          setDocument(loaded);
          setSections(loadedSections);
          setAutoAnalyzeAll(profile?.auto_analyze_documents ?? true);
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
    if (!autoAnalyzeAll || !sourceReady || autoAnalyzeStartedRef.current || !document || !sections.length || isBatchAnalyzing) return;
    const remaining = sections.filter((section) => !section.analyzed).length;
    if (!remaining) return;
    autoAnalyzeStartedRef.current = true;
    const timer = window.setTimeout(() => {
      autoStudySections(sections.length);
    }, 1200);
    return () => window.clearTimeout(timer);
  }, [autoAnalyzeAll, document, isBatchAnalyzing, sections, sourceReady]);

  useEffect(() => {
    stopPreparationRef.current = stopPreparation;
  }, [stopPreparation]);

  useEffect(() => {
    if (!continuePreparationKey || !document || !sections.length || isBatchAnalyzing) return;
    autoStudySections(sections.length);
  }, [continuePreparationKey]);

  useEffect(() => {
    setSectionAnalysis(null);
    setSectionAnalysisIndex(null);
    setError("");
    if (currentSection && !currentSection.analyzed) onSectionLesson?.(null);
  }, [currentSection?.analyzed, currentSection?.index, onSectionLesson, pageIndex]);

  useEffect(() => {
    let cancelled = false;
    if (!document || !currentSection?.analyzed || sectionAnalysisIndex === currentSection.index) return;
    api
      .getDocumentSectionAnalysis(document.id, currentSection.index)
      .then((cached) => {
        if (cancelled) return;
        setSectionAnalysis(cached);
        setSectionAnalysisIndex(currentSection.index);
        onSectionLesson?.(buildSectionLessonSelection(cached, sections, pageIndex));
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
    onSourcePageChange?.(currentPdfPage);
    sectionDrivenPdfPageRef.current = currentPdfPage;
  }, [currentPdfPage, onSourcePageChange]);

  useEffect(() => {
    currentPageGroupRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
      inline: "center"
    });
  }, [currentPdfPage]);

  useEffect(() => {
    if (!requestedSourcePage || !sections.length) return;
    if (requestedSourcePage === sectionDrivenPdfPageRef.current) return;
    if (currentPdfPage === requestedSourcePage) return;
    const matchingIndex = sections.findIndex((section) => pdfPageFromLabel(section.source_label) === requestedSourcePage);
    if (matchingIndex >= 0 && matchingIndex !== pageIndex) setPageIndex(matchingIndex);
  }, [currentPdfPage, pageIndex, requestedSourcePage, sections]);

  useEffect(() => {
    const saved = readAutoStudyProgress(progressStorageKey);
    if (saved && !batchStatus) {
      setBatchStatus(saved.status);
    }
  }, [batchStatus, progressStorageKey]);

  useEffect(() => {
    if (!sections.length) {
      onPreparationStatus?.(null);
      return;
    }
    onPreparationStatus?.({
      message: allSectionsAnalyzed ? "All section lessons are ready." : batchStatus || "Automatic section-by-section preparation is on.",
      mode: "one-by-one",
      running: isBatchAnalyzing,
      ready: analyzedCount,
      total: sections.length
    });
    if (isBatchAnalyzing) {
      writeGlobalActivity({
        label: "Analyzing document sections",
        detail: `${batchStatus || "Preparing sections one by one"} · ${analyzedCount}/${sections.length} ready`,
        href: `/analysis/${documentId}`,
        updatedAt: Date.now()
      });
    } else {
      if (allSectionsAnalyzed) clearGlobalActivity();
    }
  }, [allSectionsAnalyzed, analyzedCount, batchStatus, isBatchAnalyzing, onPreparationStatus, sections.length]);

  useEffect(() => {
    if (!isBatchAnalyzing) return;
    const timer = window.setInterval(() => {
      writeGlobalActivity({
        label: "Analyzing document sections",
        detail: `${batchStatus || "Preparing sections one by one"} · ${analyzedCount}/${sections.length} ready`,
        href: `/analysis/${documentId}`,
        updatedAt: Date.now()
      });
    }, 5000);
    return () => window.clearInterval(timer);
  }, [analyzedCount, batchStatus, documentId, isBatchAnalyzing, sections.length]);

  async function analyzeSectionAt(index: number, options: { keepBusy?: boolean; stayOnCurrent?: boolean; showLesson?: boolean } = {}) {
    const section = sections[index];
    if (!document || !section || !section.text.trim()) return;
    if (!options.stayOnCurrent) goToSection(index);
    setIsAnalyzing(true);
    setError("");
    try {
      const created = await api.analyzeDocumentSection(document.id, section.index);
      if (options.showLesson !== false && (!options.stayOnCurrent || index === pageIndex)) {
        setSectionAnalysis(created);
        setSectionAnalysisIndex(section.index);
        onSectionLesson?.(buildSectionLessonSelection(created, sections, index));
      }
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

  function goToSection(index: number) {
    const nextSection = sections[index];
    const pdfPage = pdfPageFromLabel(nextSection?.source_label ?? null);
    sectionDrivenPdfPageRef.current = pdfPage;
    onSourcePageChange?.(pdfPage);
    setPageIndex(index);
  }

  async function autoStudySections(sectionCount: number) {
    const plannedIndices = nextUnanalyzedSectionIndices(sections, pageIndex, sectionCount);
    if (!plannedIndices.length || isBatchAnalyzing) return;
    setIsBatchAnalyzing(true);
    setBatchStatus("");
    const plannedCount = plannedIndices.length;
    writeAutoStudyProgress(progressStorageKey, {
      status: `Starting analysis for ${plannedCount} section(s)...`,
      completed: 0,
      planned: plannedCount,
      updatedAt: Date.now()
    });
    let completed = 0;
    let paused = false;
    try {
      const runningStatus = `Preparing paper in the background: 0 / ${plannedCount} sections ready.`;
      setBatchStatus(runningStatus);
      writeAutoStudyProgress(progressStorageKey, {
        status: runningStatus,
        completed: 0,
        planned: plannedCount,
        updatedAt: Date.now()
      });
      for (const index of plannedIndices) {
        if (stopPreparationRef.current) {
          const status = `Preparation paused: ${completed} section${completed === 1 ? "" : "s"} finished in this run.`;
          paused = true;
          setBatchStatus(status);
          writeAutoStudyProgress(progressStorageKey, {
            status,
            completed,
            planned: plannedCount,
            updatedAt: Date.now()
          });
          break;
        }
        const sectionNumber = sections[index].section_number;
        const statusBefore = `Preparing section ${sectionNumber} / ${sections.length} one by one...`;
        setBatchStatus(statusBefore);
        const result = await api.analyzeDocumentSection(documentId, sections[index].index);
        completed += 1;
        setSections((current) =>
          current.map((section) => (section.index === sections[index].index ? { ...section, analyzed: true } : section))
        );
        onSectionAnalyzed?.();
        if (index === pageIndex) {
          setSectionAnalysis(result);
          setSectionAnalysisIndex(sections[index].index);
          onSectionLesson?.(buildSectionLessonSelection(result, sections, index));
        }
        const status = `Prepared ${completed} / ${plannedCount} remaining sections.`;
        setBatchStatus(status);
        writeAutoStudyProgress(progressStorageKey, {
          status,
          completed,
          planned: plannedCount,
          updatedAt: Date.now()
        });
        if (stopPreparationRef.current) {
          const pausedStatus = `Preparation paused after section ${sectionNumber}. Continue when ready.`;
          paused = true;
          setBatchStatus(pausedStatus);
          writeAutoStudyProgress(progressStorageKey, {
            status: pausedStatus,
            completed,
            planned: plannedCount,
            updatedAt: Date.now()
          });
          break;
        }
      }
      const updatedSections = await api.listDocumentSections(documentId);
      setSections(updatedSections);
      if (paused) return;
      const status = `Background preparation complete: ${completed} section${completed === 1 ? "" : "s"} ready.`;
      setBatchStatus(status);
      writeAutoStudyProgress(progressStorageKey, {
        status,
        completed,
        planned: plannedCount,
        updatedAt: Date.now()
      });
    } catch {
      const status = completed
        ? `Paper prepared through ${completed} section${completed === 1 ? "" : "s"}. Retry to continue.`
        : "Could not analyze this section. Retry when the local model is ready.";
      setBatchStatus(status);
      writeAutoStudyProgress(progressStorageKey, {
        status,
        completed,
        planned: plannedCount,
        updatedAt: Date.now()
      });
    } finally {
      setIsBatchAnalyzing(false);
    }
  }

  return (
    <section className="rounded-lg border border-line bg-panel shadow-material">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line p-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Current section</p>
          <h2 className="mt-1 text-lg font-semibold">
            PDF page {currentPdfPage ?? "?"} · S{currentPageSectionNumber ?? currentSection?.section_number ?? pageIndex + 1}
          </h2>
          <p className="mt-1 text-xs font-semibold text-neutral-600">
            Document section {currentSection?.section_number ?? pageIndex + 1} / {currentSection?.total_sections ?? Math.max(sections.length, 1)}
          </p>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-700">
            {currentSection?.preview || "Choose a section from the strip below."}
          </p>
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 lg:w-auto lg:justify-end">
          {document.source_type === "pdf" && !document.has_original_file ? (
            <>
              <button
                type="button"
                onClick={() => attachInputRef.current?.click()}
                disabled={isAttaching}
                className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-semibold text-ink hover:bg-surface disabled:opacity-50"
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
            disabled={isAnalyzing || !currentSection || !page.trim()}
            className="inline-flex items-center gap-2 rounded-md bg-accent px-3 py-2 text-sm font-semibold text-white disabled:bg-neutral-300 disabled:text-neutral-600"
          >
            <ScanText size={16} />
            {isAnalyzing ? "Analyzing..." : currentSection?.analyzed ? "Re-analyze section" : "Analyze section"}
          </button>
        </div>
      </div>
      {sections.length ? (
        <div className="border-b border-line px-5 py-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Section navigator</p>
            <p className="text-xs font-semibold text-neutral-600">Green sections are ready</p>
          </div>
          <div className="flex gap-2 overflow-x-auto">
          {sectionGroups.map((group) => {
            const isCurrentPageGroup = group.pdfPage === currentPdfPage;
            return (
            <div
              key={group.key}
              ref={isCurrentPageGroup ? currentPageGroupRef : null}
              className={`shrink-0 rounded-md border px-2 py-1.5 transition ${
                isCurrentPageGroup ? "border-accent bg-blue-50 shadow-sm" : "border-line bg-surface"
              }`}
            >
              <div className="mb-2 flex items-center justify-between gap-3">
                <p className={`text-[11px] font-semibold uppercase tracking-wide ${isCurrentPageGroup ? "text-accent" : "text-neutral-500"}`}>
                  {group.label}
                </p>
              </div>
              <div className="flex gap-1">
                {group.items.map(({ section, index, localNumber }) => (
                  <button
                    key={section.index}
                    type="button"
                    onClick={() => goToSection(index)}
                    className={`flex h-8 min-w-12 items-center justify-center rounded-md border px-2 text-[11px] font-semibold ${
                      index === pageIndex
                        ? "border-accent bg-accent text-white"
                        : section.analyzed
                          ? "border-green-200 bg-green-50 text-green-700"
                          : "border-line bg-panel text-neutral-500 hover:bg-white"
                    }`}
                    title={`${group.label} / S${localNumber} on page / document section ${section.section_number}${
                      section.analyzed ? " analyzed" : " not analyzed"
                    }`}
                  >
                    <span>S{localNumber}</span>
                  </button>
                ))}
              </div>
            </div>
            );
          })}
          </div>
        </div>
      ) : null}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-3">
        <button
          type="button"
          onClick={() => goToSection(Math.max(0, pageIndex - 1))}
          disabled={pageIndex === 0}
          className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-xs font-semibold text-ink hover:bg-surface disabled:opacity-40"
        >
          <ChevronLeft size={15} />
          Previous section
        </button>
        <div className="text-center">
          <p className={`rounded-full px-3 py-1 text-xs font-semibold ${currentSection?.analyzed ? "bg-green-50 text-green-700" : "bg-neutral-100 text-neutral-500"}`}>
            {currentSection?.analyzed ? "Ready" : "Not ready"}
          </p>
        </div>
        <button
          type="button"
          onClick={() => goToSection(Math.min(sections.length - 1, pageIndex + 1))}
          disabled={!sections.length || pageIndex >= sections.length - 1}
          className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-xs font-semibold text-ink hover:bg-surface disabled:opacity-40"
        >
          Next section
          <ChevronRight size={15} />
        </button>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface px-5 py-3">
        <div className="max-w-2xl space-y-1">
          {currentSection?.preview ? <p className="text-sm font-medium leading-6 text-ink">{currentSection.preview}</p> : null}
          <p className="text-xs leading-5 text-neutral-600">
            {currentSection?.analyzed
              ? "Open the lesson from this section, then save words and expressions worth reviewing."
              : "No lesson has been built for this section yet. By default, GemmaLens prepares all sections in the background while the first page stays readable."}
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
          sectionLabel={formatSectionLabel(currentSection, currentPdfPage, currentPageSectionNumber)}
          embedded
        />
      ) : null}
    </section>
  );
}

export function SectionLessonCard({
  analysis,
  sectionNumber,
  sectionLabel,
  embedded = false
}: {
  analysis: AnalysisResult;
  sectionNumber: number;
  sectionLabel?: string;
  isAnalyzingNext?: boolean;
  embedded?: boolean;
}) {
  const [saved, setSaved] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState<string | null>(null);
  const concepts = (analysis.concepts ?? []).slice(0, 4);
  const terms = analysis.terms.slice(0, 6);
  const phrases = analysis.phrases.filter((phrase) => isUsefulExpression(phrase.phrase)).slice(0, 5);
  const studyNotes = analysis.summaries.study_notes.slice(0, 3);
  const className = embedded
    ? "border-t border-line p-5"
    : "rounded-lg border border-line bg-panel p-5 shadow-material";

  async function saveItem(item: LessonSaveItem) {
    const key = `${item.item_type}:${item.text}`;
    setSaving(key);
    try {
      await api.saveDictionaryItem({
        ...item,
        document_id: analysis.document_id
      });
      setSaved((current) => new Set(current).add(key));
    } finally {
      setSaving(null);
    }
  }

  return (
    <div className={className}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Section {sectionNumber} lesson</p>
          {sectionLabel ? <p className="mt-1 text-xs font-semibold text-neutral-600">{sectionLabel}</p> : null}
          <h3 className="mt-1 text-lg font-semibold">{analysis.summaries.one_line}</h3>
        </div>
        <p className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-accent">
          {concepts.length} concepts · {terms.length} terms · {phrases.length} expressions
        </p>
      </div>
      <p className="mt-2 text-sm leading-6 text-neutral-700">{analysis.summaries.simple}</p>
      <div className="mt-5 grid gap-4">
        <MiniList
          title="Words and terms"
          supportLabel="Native gloss"
          meaningLabel="English meaning"
          rows={terms.map((term) => ({
            item_type: "term" as const,
            text: term.term,
            meaning: term.meaning,
            supportMeaning: term.support_language_meaning,
            source_sentence: term.source_sentence
          }))}
          saved={saved}
          saving={saving}
          onSave={saveItem}
        />
        <MiniList
          title="Academic expressions"
          supportLabel="Native usage"
          meaningLabel="English function"
          rows={phrases.map((phrase) => ({
            item_type: "phrase" as const,
            text: phrase.phrase,
            meaning: phrase.explanation,
            supportMeaning: phrase.support_language_explanation,
            source_sentence: phrase.source_sentence
          }))}
          saved={saved}
          saving={saving}
          onSave={saveItem}
        />
      </div>
      <div className="mt-4 rounded-md border border-line bg-surface p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">How to read this section</p>
        <p className="mt-2 text-sm leading-6 text-neutral-700">{analysis.summaries.academic}</p>
        {studyNotes.length ? (
          <ul className="mt-3 space-y-2">
            {studyNotes.map((note) => (
              <li key={note} className="text-sm leading-6 text-neutral-700">
                <span className="mr-2 font-semibold text-accent">Focus</span>
                {note}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
      {concepts.length ? (
        <div className="mt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Concept anchors</p>
          <div className="mt-2 grid gap-3">
            {concepts.map((concept) => {
              const key = `concept:${concept.concept}`;
              const isSaved = saved.has(key);
              return (
                <div key={concept.concept} className="rounded-md border border-line bg-surface p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-ink">{concept.concept}</p>
                      <p className="mt-1 text-sm leading-6 text-neutral-700">{concept.explanation || concept.why_it_matters}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        saveItem({
                          item_type: "concept",
                          text: concept.concept,
                          meaning: concept.explanation || concept.why_it_matters,
                          source_sentence: concept.source_sentence
                        })
                      }
                      disabled={isSaved || saving === key}
                      className="inline-flex shrink-0 items-center gap-1 rounded-md border border-line bg-panel px-2.5 py-1.5 text-xs font-semibold text-ink hover:bg-white disabled:text-green-700"
                      title={isSaved ? "Saved to dictionary" : "Save concept"}
                    >
                      {isSaved ? <CheckCircle2 size={13} /> : <BookmarkPlus size={13} />}
                      {isSaved ? "Saved" : saving === key ? "Saving" : "Save"}
                    </button>
                  </div>
                  {concept.source_sentence ? (
                    <p className="mt-3 border-l-2 border-blue-200 pl-3 text-xs leading-5 text-neutral-600">{truncateText(concept.source_sentence, 260)}</p>
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
      {analysis.sentences[0] ? (
        <div className="mt-5 rounded-md border border-line bg-surface p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Hard sentence pattern</p>
          <p className="mt-2 text-sm font-semibold text-ink">{analysis.sentences[0].core_structure}</p>
          <p className="mt-2 text-sm leading-6 text-neutral-700">{analysis.sentences[0].simplified_version}</p>
          <p className="mt-2 text-sm leading-6 text-neutral-700">{analysis.sentences[0].korean_explanation}</p>
          <p className="mt-3 border-l-2 border-blue-200 pl-3 text-xs leading-5 text-neutral-600">
            {truncateText(analysis.sentences[0].sentence, 320)}
          </p>
        </div>
      ) : null}
    </div>
  );
}

type LessonSaveItem = {
  item_type: "term" | "phrase" | "sentence" | "concept";
  text: string;
  meaning?: string;
  supportMeaning?: string;
  source_sentence?: string;
};

export type SectionLessonSelection = {
  analysis: AnalysisResult;
  sectionNumber: number;
  sectionLabel?: string;
};

export type SectionPreparationStatus = {
  message: string;
  mode: "one-by-one";
  running: boolean;
  ready: number;
  total: number;
};

function MiniList({
  title,
  supportLabel,
  meaningLabel,
  rows,
  saved,
  saving,
  onSave
}: {
  title: string;
  supportLabel: string;
  meaningLabel: string;
  rows: LessonSaveItem[];
  saved: Set<string>;
  saving: string | null;
  onSave: (item: LessonSaveItem) => Promise<void>;
}) {
  return (
    <div className="rounded-md border border-line bg-surface p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{title}</p>
      <p className="mt-1 text-xs leading-5 text-neutral-600">Use these as quick glosses while reading; save only items worth reviewing later.</p>
      {rows.length ? (
        <div className="mt-3 space-y-3">
          {rows.map((row) => {
            const key = `${row.item_type}:${row.text}`;
            const isSaved = saved.has(key);
            return (
            <div key={row.text} className="rounded-md border border-line bg-panel p-3">
              <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-ink">{row.text}</p>
                {row.supportMeaning ? (
                  <div className="mt-2 rounded-md bg-blue-50 px-3 py-2">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-accent">{supportLabel}</p>
                    <p className="mt-1 text-sm leading-5 text-ink">{row.supportMeaning}</p>
                  </div>
                ) : null}
                <div className="mt-2 rounded-md bg-surface px-3 py-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">{meaningLabel}</p>
                  <p className="mt-1 text-xs leading-5 text-neutral-700">{row.meaning}</p>
                </div>
                {row.source_sentence ? (
                  <div className="mt-2 border-l-2 border-line pl-3">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Source</p>
                    <p className="mt-1 text-xs leading-5 text-neutral-500">{truncateText(row.source_sentence, 220)}</p>
                  </div>
                ) : null}
              </div>
              <button
                type="button"
                onClick={() => onSave(row)}
                disabled={isSaved || saving === key}
                className="inline-flex shrink-0 items-center gap-1 rounded-md border border-line bg-panel px-2.5 py-1.5 text-xs font-semibold text-ink hover:bg-white disabled:text-green-700"
              >
                {isSaved ? <CheckCircle2 size={13} /> : <BookmarkPlus size={13} />}
                {isSaved ? "Saved" : saving === key ? "Saving" : "Save"}
              </button>
              </div>
            </div>
            );
          })}
        </div>
      ) : (
        <p className="mt-3 text-sm text-neutral-600">No strong items found for this section.</p>
      )}
    </div>
  );
}

function isUsefulExpression(value: string) {
  const normalized = value.trim().toLowerCase();
  const blocked = new Set(["the best performing models", "best performing models", "performing models"]);
  return Boolean(normalized) && !blocked.has(normalized);
}

function truncateText(value: string, limit: number) {
  const normalized = value
    .replace(/\[\[GEMMALENS_PDF_PAGE:\d+]]/g, " ")
    .split(/\s+/)
    .join(" ")
    .trim();
  if (normalized.length <= limit) return normalized;
  return `${normalized.slice(0, limit).trim()}...`;
}

function pdfPageFromLabel(label: string | null) {
  const match = label?.match(/^PDF page (\d+)$/);
  return match ? Number(match[1]) : null;
}

function groupSectionsByPdfPage(sections: DocumentSection[]) {
  const groups: Array<{
    key: string;
    label: string;
    pdfPage: number | null;
    items: Array<{ section: DocumentSection; index: number; localNumber: number }>;
  }> = [];
  const lookup = new Map<string, (typeof groups)[number]>();

  sections.forEach((section, index) => {
    const pdfPage = pdfPageFromLabel(section.source_label);
    const key = pdfPage ? `pdf-${pdfPage}` : "unknown";
    let group = lookup.get(key);
    if (!group) {
      group = { key, label: "", pdfPage, items: [] };
      lookup.set(key, group);
      groups.push(group);
    }
    group.items.push({ section, index, localNumber: group.items.length + 1 });
    group.label = pdfPage ? `PDF page ${pdfPage}` : "PDF page unknown";
  });

  return groups;
}

function sectionNumberWithinPdfPage(sections: DocumentSection[], index: number) {
  const section = sections[index];
  if (!section) return null;
  const page = pdfPageFromLabel(section.source_label);
  let localNumber = 0;
  for (let cursor = 0; cursor <= index; cursor += 1) {
    if (pdfPageFromLabel(sections[cursor]?.source_label ?? null) === page) {
      localNumber += 1;
    }
  }
  return localNumber || null;
}

function buildSectionLessonSelection(analysis: AnalysisResult, sections: DocumentSection[], index: number): SectionLessonSelection {
  const section = sections[index];
  const pdfPage = pdfPageFromLabel(section?.source_label ?? null);
  const localSection = sectionNumberWithinPdfPage(sections, index);
  return {
    analysis,
    sectionNumber: section?.section_number ?? index + 1,
    sectionLabel: formatSectionLabel(section, pdfPage, localSection)
  };
}

function formatSectionLabel(section: DocumentSection | undefined, pdfPage: number | null, localSection: number | null) {
  const global = section?.section_number ?? null;
  const total = section?.total_sections ?? null;
  const pageLabel = pdfPage ? `PDF page ${pdfPage}` : "PDF page unknown";
  const localLabel = localSection ? `S${localSection} on this page` : "section on page unknown";
  const globalLabel = global && total ? `document section ${global} / ${total}` : "document section unknown";
  return `${pageLabel} · ${localLabel} · ${globalLabel}`;
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

function writeGlobalActivity(activity: { label: string; detail: string; href?: string; updatedAt: number }) {
  try {
    window.localStorage.setItem("gemmalens:active-task", JSON.stringify(activity));
  } catch {
    // Global status is best-effort UI state.
  }
}

function clearGlobalActivity() {
  try {
    window.localStorage.removeItem("gemmalens:active-task");
  } catch {
    // Global status is best-effort UI state.
  }
}
