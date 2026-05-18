"use client";

import { BookmarkPlus, CheckCircle2, ChevronsLeft, ChevronsRight, ChevronLeft, ChevronRight, CornerLeftUp, Eye, EyeOff, Paperclip, ScanText } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { AnalysisResult, DocumentRead, DocumentSection } from "@/lib/types";

export function DocumentPageReader({
  documentId,
  onSectionAnalyzed,
  onSectionLesson,
  onSectionState,
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
  onSectionState?: (state: SectionReaderState | null) => void;
  onPreparationStatus?: (status: SectionPreparationStatus | null) => void;
  stopPreparation?: boolean;
  continuePreparationKey?: number;
  onSourcePageChange?: (page: number | null) => void;
  requestedSourcePage?: number | null;
  sourceReady?: boolean;
  hideInlineLesson?: boolean;
}) {
  const [supportLanguage, setSupportLanguage] = useState<string>("Korean");
  const [document, setDocument] = useState<DocumentRead | null>(null);
  const [sections, setSections] = useState<DocumentSection[]>([]);
  const [pageIndex, setPageIndex] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isBatchAnalyzing, setIsBatchAnalyzing] = useState(false);
  const [batchStatus, setBatchStatus] = useState("");
  const [isAttaching, setIsAttaching] = useState(false);
  const [autoAnalyzeAll, setAutoAnalyzeAll] = useState(false);
  const [initialSectionReady, setInitialSectionReady] = useState(false);
  const [sectionAnalysis, setSectionAnalysis] = useState<AnalysisResult | null>(null);
  const [sectionAnalysisIndex, setSectionAnalysisIndex] = useState<number | null>(null);
  const [error, setError] = useState("");
  const attachInputRef = useRef<HTMLInputElement>(null);
  const sectionDrivenPdfPageRef = useRef<number | null>(null);
  const autoAnalyzeStartedRef = useRef(false);
  const initialSectionStartedRef = useRef(false);
  const stopPreparationRef = useRef(false);
  const currentPageGroupRef = useRef<HTMLDivElement | null>(null);
  const firstSection = sections[0];
  const currentSection = sections[pageIndex];
  const page = currentSection?.text ?? "";
  const analyzedCount = sections.filter((section) => section.analyzed).length;
  const allSectionsAnalyzed = Boolean(sections.length && analyzedCount >= sections.length);
  const progressStorageKey = `gemmalens:auto-study:${documentId}`;
  const sectionGroups = groupSectionsByPdfPage(sections);
  const currentPdfPage = pdfPageFromLabel(currentSection?.source_label ?? null);
  const currentPageSectionNumber = currentSection ? sectionNumberWithinPdfPage(sections, pageIndex) : null;
  const currentSectionTitle = formatSectionTitle(currentSection);
  const firstSourcePage = pdfPageFromLabel(firstSection?.source_label ?? null) ?? 1;
  const previousPageIndex = findAdjacentPdfPageIndex(sections, pageIndex, -1);
  const nextPageIndex = findAdjacentPdfPageIndex(sections, pageIndex, 1);
  const parentSectionIndex = currentSection?.continuation
    ? findParentSectionIndex(sections, pageIndex)
    : null;
  const parentSection = parentSectionIndex !== null ? sections[parentSectionIndex] : null;
  const parentPdfPage = parentSection ? pdfPageFromLabel(parentSection.source_label) : null;
  const currentSectionSummary =
    !initialSectionReady
      ? "Preparing the first lesson before opening the workspace."
      : sectionAnalysis && sectionAnalysisIndex === currentSection?.index
      ? sectionAnalysis.summaries.one_line
      : currentSection?.analyzed
        ? "Loading this lesson..."
        : isBatchAnalyzing
          ? "This part is still preparing. You can keep reading ready parts while GemmaLens works in the background."
          : "Analyze this part to build its summary, terms, expressions, and sentence patterns.";

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.getDocument(documentId), api.listDocumentSections(documentId), api.getProfile().catch(() => null)])
      .then(([loaded, loadedSections, profile]) => {
        if (!cancelled) {
          setDocument(loaded);
          setSections(loadedSections);
          setAutoAnalyzeAll(profile?.auto_analyze_documents ?? true);
          if (profile?.support_language) setSupportLanguage(profile.support_language);
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
    if (!sourceReady || !document || !sections.length || initialSectionReady || initialSectionStartedRef.current) return;
    if (!firstSection || firstSection.analyzed) {
      setInitialSectionReady(true);
      return;
    }
    initialSectionStartedRef.current = true;
    setIsBatchAnalyzing(true);
    setBatchStatus("Preparing the first section so the lesson opens ready.");
    api
      .analyzeDocumentPage(document.id, firstSourcePage)
      .then(async () => {
        const updatedSections = await api.listDocumentSections(document.id);
        setSections(updatedSections);
        const firstIndex = updatedSections.findIndex((section) => section.index === firstSection.index);
        if (pageIndex === 0 && firstIndex >= 0) {
          const result = await api.getDocumentSectionAnalysis(document.id, firstSection.index);
          setSectionAnalysis(result);
          setSectionAnalysisIndex(firstSection.index);
          onSectionLesson?.(buildSectionLessonSelection(result, updatedSections, firstIndex));
        }
        onSectionAnalyzed?.();
        setInitialSectionReady(true);
        setBatchStatus("First page ready. Preparing remaining pages in the background.");
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Could not prepare the first section.");
        setInitialSectionReady(true);
        initialSectionStartedRef.current = false;
      })
      .finally(() => {
        setIsBatchAnalyzing(false);
      });
  }, [document, firstSection?.analyzed, firstSection?.index, firstSourcePage, initialSectionReady, onSectionAnalyzed, onSectionLesson, pageIndex, sourceReady]);

  useEffect(() => {
    if (!initialSectionReady || !autoAnalyzeAll || !sourceReady || autoAnalyzeStartedRef.current || !document || !sections.length || isBatchAnalyzing) return;
    const remaining = sections.filter((section) => !section.analyzed).length;
    if (!remaining) return;
    autoAnalyzeStartedRef.current = true;
    const timer = window.setTimeout(() => {
      autoStudyPages(sections.length);
    }, 1200);
    return () => window.clearTimeout(timer);
  }, [autoAnalyzeAll, document, initialSectionReady, isBatchAnalyzing, sections, sourceReady]);

  useEffect(() => {
    stopPreparationRef.current = stopPreparation;
  }, [stopPreparation]);

  useEffect(() => {
    if (!continuePreparationKey || !document || !sections.length || isBatchAnalyzing) return;
    autoStudyPages(sections.length);
  }, [continuePreparationKey]);

  useEffect(() => {
    setSectionAnalysis(null);
    setSectionAnalysisIndex(null);
    setError("");
    if (currentSection && !currentSection.analyzed) onSectionLesson?.(null);
  }, [currentSection?.analyzed, currentSection?.index, onSectionLesson, pageIndex]);

  useEffect(() => {
    if (!currentSection) {
      onSectionState?.(null);
      return;
    }
    onSectionState?.({
      analyzed: currentSection.analyzed,
      sectionNumber: currentSection.section_number,
      sectionLabel: formatSectionLabel(currentSection, currentPdfPage, currentPageSectionNumber),
      isBatchAnalyzing
    });
  }, [currentPageSectionNumber, currentPdfPage, currentSection, isBatchAnalyzing, onSectionState]);

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
      message: allSectionsAnalyzed ? "All page lessons are ready." : batchStatus || "Automatic page preparation is on.",
      mode: "page-batch",
      running: isBatchAnalyzing,
      ready: analyzedCount,
      total: sections.length
    });
    if (isBatchAnalyzing) {
      writeGlobalActivity({
        label: "Analyzing",
        detail: `${batchStatus || "Preparing pages"} · ${analyzedCount}/${sections.length} sections ready`,
        href: `/analysis/${documentId}`,
        updatedAt: Date.now()
      });
    } else {
      clearGlobalActivity();
    }
  }, [allSectionsAnalyzed, analyzedCount, batchStatus, documentId, isBatchAnalyzing, onPreparationStatus, sections.length]);

  useEffect(() => {
    if (!isBatchAnalyzing) return;
    const timer = window.setInterval(() => {
      writeGlobalActivity({
        label: "Analyzing",
        detail: `${batchStatus || "Preparing pages"} · ${analyzedCount}/${sections.length} sections ready`,
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
      const created = await api.analyzeDocumentSection(document.id, section.index, { force: section.analyzed });
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

  if (!document) return null;
  if (document.source_type === "transcript" || document.source_type === "video_segment") return null;

  function goToSection(index: number) {
    const nextSection = sections[index];
    const pdfPage = pdfPageFromLabel(nextSection?.source_label ?? null);
    sectionDrivenPdfPageRef.current = pdfPage;
    onSourcePageChange?.(pdfPage);
    setPageIndex(index);
  }

  async function autoStudyPages(pageLimit: number) {
    const plannedPages = nextUnanalyzedPageNumbers(sections, pageLimit);
    if (!plannedPages.length || isBatchAnalyzing) return;
    setIsBatchAnalyzing(true);
    setBatchStatus("");
    const plannedCount = plannedPages.length;
    writeAutoStudyProgress(progressStorageKey, {
      status: `Starting page preparation for ${plannedCount} page(s)...`,
      completed: 0,
      planned: plannedCount,
      updatedAt: Date.now()
    });
    let completed = 0;
    let paused = false;
    try {
      const runningStatus = `Preparing pages in the background: 0 / ${plannedCount} pages ready.`;
      setBatchStatus(runningStatus);
      writeAutoStudyProgress(progressStorageKey, {
        status: runningStatus,
        completed: 0,
        planned: plannedCount,
        updatedAt: Date.now()
      });
      for (const pageNumber of plannedPages) {
        if (stopPreparationRef.current) {
          const status = `Preparation paused: ${completed} page${completed === 1 ? "" : "s"} finished in this run.`;
          paused = true;
          setBatchStatus(status);
          writeAutoStudyProgress(progressStorageKey, { status, completed, planned: plannedCount, updatedAt: Date.now() });
          break;
        }
        const statusBefore = `Preparing page ${pageNumber}...`;
        setBatchStatus(statusBefore);
        await api.analyzeDocumentPage(documentId, pageNumber);
        completed += 1;
        const updatedSections = await api.listDocumentSections(documentId);
        setSections(updatedSections);
        onSectionAnalyzed?.();
        const visibleSection = updatedSections[pageIndex];
        if (visibleSection?.analyzed) {
          try {
            const result = await api.getDocumentSectionAnalysis(documentId, visibleSection.index);
            setSectionAnalysis(result);
            setSectionAnalysisIndex(visibleSection.index);
            onSectionLesson?.(buildSectionLessonSelection(result, updatedSections, pageIndex));
          } catch {
            // The page may not contain the currently selected section.
          }
        }
        const status = `Prepared ${completed} / ${plannedCount} remaining pages.`;
        setBatchStatus(status);
        writeAutoStudyProgress(progressStorageKey, { status, completed, planned: plannedCount, updatedAt: Date.now() });
        if (stopPreparationRef.current) {
          const pausedStatus = `Preparation paused after page ${pageNumber}.`;
          paused = true;
          setBatchStatus(pausedStatus);
          writeAutoStudyProgress(progressStorageKey, { status: pausedStatus, completed, planned: plannedCount, updatedAt: Date.now() });
          break;
        }
      }
      if (paused) {
        clearGlobalActivity();
        return;
      }
      const status = `Background preparation complete: ${completed} page${completed === 1 ? "" : "s"} ready.`;
      setBatchStatus(status);
      writeAutoStudyProgress(progressStorageKey, { status, completed, planned: plannedCount, updatedAt: Date.now() });
    } catch {
      const status = completed
        ? `Prepared ${completed} page${completed === 1 ? "" : "s"}. Retry to continue.`
        : "Could not prepare this page. Retry when the local model is ready.";
      setBatchStatus(status);
      writeAutoStudyProgress(progressStorageKey, { status, completed, planned: plannedCount, updatedAt: Date.now() });
    } finally {
      setIsBatchAnalyzing(false);
    }
  }

  const totalPdfPages = sectionGroups.length || 1;

  return (
    <section className="rounded-lg border border-line bg-panel shadow-material">
      {/* Compact navigation bar */}
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-2.5">
        <div className="flex shrink-0 items-center gap-1.5">
          {/* Page / section nav with inline page counter */}
          <div className="flex items-center rounded-md border border-line bg-surface">
            <button
              type="button"
              onClick={() => { if (previousPageIndex !== null) goToSection(previousPageIndex); }}
              disabled={previousPageIndex === null}
              className="inline-flex h-8 w-8 items-center justify-center text-ink hover:bg-white disabled:opacity-35"
              aria-label="Previous PDF page"
            >
              <ChevronsLeft size={14} />
            </button>
            <button
              type="button"
              onClick={() => goToSection(Math.max(0, pageIndex - 1))}
              disabled={pageIndex === 0}
              className="inline-flex h-8 w-8 items-center justify-center border-l border-line text-ink hover:bg-white disabled:opacity-35"
              aria-label="Previous section"
            >
              <ChevronLeft size={14} />
            </button>
            <span className="flex h-8 min-w-[3rem] items-center justify-center border-l border-line px-2 text-xs font-semibold tabular-nums text-neutral-600">
              {currentPdfPage ?? "?"} / {totalPdfPages}
            </span>
            <button
              type="button"
              onClick={() => goToSection(Math.min(sections.length - 1, pageIndex + 1))}
              disabled={!sections.length || pageIndex >= sections.length - 1}
              className="inline-flex h-8 w-8 items-center justify-center border-l border-line text-ink hover:bg-white disabled:opacity-35"
              aria-label="Next section"
            >
              <ChevronRight size={14} />
            </button>
            <button
              type="button"
              onClick={() => { if (nextPageIndex !== null) goToSection(nextPageIndex); }}
              disabled={nextPageIndex === null}
              className="inline-flex h-8 w-8 items-center justify-center border-l border-line text-ink hover:bg-white disabled:opacity-35"
              aria-label="Next PDF page"
            >
              <ChevronsRight size={14} />
            </button>
          </div>
          {/* Rebuild / build lesson */}
          <button
            type="button"
            onClick={analyzePage}
            disabled={isAnalyzing || isBatchAnalyzing || !currentSection || !page.trim()}
            className="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface px-2.5 py-1.5 text-xs font-semibold text-ink hover:bg-white disabled:opacity-40"
            title={isBatchAnalyzing ? "Pause background preparation first" : undefined}
          >
            <ScanText size={13} />
            {isAnalyzing ? "Analyzing…" : currentSection?.analyzed ? "Rebuild" : "Build notes"}
          </button>
          {/* Attach PDF button */}
          {document.source_type === "pdf" && !document.has_original_file ? (
            <>
              <button
                type="button"
                onClick={() => attachInputRef.current?.click()}
                disabled={isAttaching}
                className="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface px-2.5 py-1.5 text-xs font-semibold text-ink hover:bg-white disabled:opacity-50"
              >
                <Paperclip size={13} />
                {isAttaching ? "Attaching…" : "Attach PDF"}
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
        </div>
      </div>
      {/* Continuation context — this section continues from a previous page */}
      {currentSection?.continuation && parentSection ? (
        <div className="flex items-center gap-2 border-b border-amber-100 bg-amber-50 px-4 py-2">
          <CornerLeftUp size={13} className="shrink-0 text-amber-600" />
          <p className="min-w-0 flex-1 text-xs text-amber-700">
            Continues from page {parentPdfPage ?? "previous"} — this text is part of the same section.
          </p>
          <button
            type="button"
            onClick={() => { if (parentSectionIndex !== null) goToSection(parentSectionIndex); }}
            className="shrink-0 rounded-md border border-amber-200 bg-white px-2 py-1 text-xs font-semibold text-amber-700 hover:bg-amber-100"
          >
            View page {parentPdfPage ?? "prev"} notes
          </button>
        </div>
      ) : null}
      {/* Status message — only when section not analyzed (no shift while lesson loads) */}
      {(!sectionAnalysis || sectionAnalysisIndex !== currentSection?.index) && !currentSection?.analyzed ? (
        <p className="border-b border-line px-4 py-2.5 text-xs leading-5 text-neutral-500">
          {currentSectionSummary || "Select a section to view its notes."}
        </p>
      ) : null}
      {sections.length ? (
        <div className="border-b border-line px-4 py-2">
          <div className="mb-2 flex items-center justify-between gap-2 text-[11px] text-neutral-500">
            <span className="font-semibold tabular-nums text-neutral-600">
              {analyzedCount}/{sections.length} ready
              {isBatchAnalyzing ? <span className="ml-1.5 text-accent">· Preparing…</span> : null}
            </span>
            <div className="flex items-center gap-2">
              {sectionGroups.length ? <span>{sectionGroups.length} pages</span> : null}
              <span className="inline-flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-accent" /> Current</span>
              <span className="inline-flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-green-500" /> Ready</span>
              <span className="inline-flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-neutral-300" /> Not ready</span>
            </div>
          </div>
          <div className="flex gap-2 overflow-x-auto">
          {sectionGroups.map((group) => {
            const isCurrentPageGroup = group.pdfPage === currentPdfPage;
            return (
            <div
              key={group.key}
              ref={isCurrentPageGroup ? currentPageGroupRef : null}
              data-current-page={isCurrentPageGroup ? "true" : "false"}
              className={`shrink-0 rounded-md border px-2 py-1.5 transition ${
                isCurrentPageGroup ? "border-accent bg-blue-50 shadow-sm" : "border-line bg-surface"
              }`}
            >
              <p className={`mb-1.5 text-[11px] font-semibold ${isCurrentPageGroup ? "text-accent" : "text-neutral-500"}`}>
                Page {group.pdfPage ?? "?"}
              </p>
              <div className="flex gap-1">
                {group.items.map(({ section, index, localNumber }) => (
                  <button
                    key={section.index}
                    type="button"
                    onClick={() => goToSection(index)}
                    className={`flex h-8 min-w-12 items-center justify-center gap-0.5 rounded-md px-2 text-[11px] font-semibold transition ${
                      index === pageIndex
                        ? "border border-accent bg-accent text-white"
                        : section.analyzed
                          ? section.continuation
                            ? "border border-dashed border-green-300 bg-green-50 text-green-700"
                            : "border border-green-200 bg-green-50 text-green-700"
                          : section.continuation
                            ? "border border-dashed border-neutral-200 bg-panel text-neutral-400 hover:bg-white"
                            : "border border-line bg-panel text-neutral-500 hover:bg-white"
                    }`}
                    title={`Page ${group.pdfPage ?? "?"} / Part ${localNumber}${section.continuation ? " (continued from prev page)" : ""}${
                      section.analyzed ? " · ready" : " · not analyzed"
                    }`}
                  >
                    {section.continuation ? <span className="opacity-60">~</span> : null}
                    <span>{compactSectionNavLabel(section, localNumber)}</span>
                  </button>
                ))}
              </div>
            </div>
            );
          })}
          </div>
        </div>
      ) : null}
      <div className="flex items-center justify-end gap-2 border-b border-line px-4 py-2">
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          className="inline-flex items-center gap-1.5 rounded-md border border-line bg-panel px-2.5 py-1.5 text-xs font-semibold text-neutral-600 hover:bg-white"
        >
          {expanded ? <EyeOff size={13} /> : <Eye size={13} />}
          {expanded ? "Hide source" : "Source text"}
        </button>
      </div>
      {error ? <p className="mx-4 my-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
      {expanded ? (
        <article className="whitespace-pre-wrap p-4 text-sm leading-7 text-neutral-800">{page}</article>
      ) : null}
      {sectionAnalysis && !hideInlineLesson ? (
        <SectionLessonCard
          analysis={sectionAnalysis}
          sectionNumber={pageIndex + 1}
          sectionLabel={formatSectionLabel(currentSection, currentPdfPage, currentPageSectionNumber)}
          supportLanguage={supportLanguage}
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
  supportLanguage,
  embedded = false
}: {
  analysis: AnalysisResult;
  sectionNumber: number;
  sectionLabel?: string;
  supportLanguage?: string;
  isAnalyzingNext?: boolean;
  embedded?: boolean;
}) {
  const [saved, setSaved] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"terms" | "phrases" | "patterns" | "ideas">("terms");
  const concepts = dedupeByText(analysis.concepts ?? [], (concept) => concept.concept).slice(0, 5);
  const terms = dedupeByText(analysis.terms, (term) => term.term).slice(0, 8);
  const phrases = dedupeByText(analysis.phrases.filter((phrase) => isUsefulExpression(phrase.phrase)), (phrase) => phrase.phrase).slice(0, 5);
  const studyNotes = analysis.summaries.study_notes.slice(0, 3);
  const sentencePatterns = dedupeByText(analysis.sentences, (sentence) => sentence.core_structure || sentence.sentence).slice(0, 3);
  const firstSentence = sentencePatterns[0];
  const wrapperClass = embedded
    ? "border-t border-line"
    : "rounded-lg border border-line bg-panel shadow-material";

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

  const tabs: { id: typeof activeTab; label: string; count: number }[] = [
    { id: "terms", label: "Terms", count: terms.length },
    { id: "phrases", label: "Phrases", count: phrases.length },
    { id: "patterns", label: "Patterns", count: sentencePatterns.length },
    { id: "ideas", label: "Ideas", count: concepts.length },
  ];

  return (
    <div className={wrapperClass}>
      {/* Primary lesson summary */}
      <div className="p-5 pb-4">
        <h3 className="text-[15px] font-semibold leading-snug text-ink">{analysis.summaries.one_line}</h3>
        <p className="mt-1.5 text-sm leading-6 text-neutral-600">{analysis.summaries.academic}</p>
        {studyNotes.length ? (
          <ul className="mt-3 space-y-1.5">
            {studyNotes.map((note) => (
              <li key={note} className="flex items-start gap-2 text-sm leading-5 text-neutral-700">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                {note}
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-line">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold transition-colors ${
              activeTab === tab.id
                ? "border-b-2 border-accent text-accent"
                : "text-neutral-500 hover:text-ink"
            }`}
          >
            {tab.label}
            {tab.count > 0 ? (
              <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${
                activeTab === tab.id ? "bg-blue-100 text-accent" : "bg-neutral-100 text-neutral-500"
              }`}>
                {tab.count}
              </span>
            ) : null}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="p-4">
        {activeTab === "terms" ? (
          <MiniList
            supportLabel={`${supportLanguage ?? "Native"} gloss`}
            meaningLabel="Meaning"
            rows={terms.map((term) => ({
              item_type: "term" as const,
              text: term.term,
              meaning: stripFiller(term.meaning),
              supportMeaning: term.support_language_meaning,
              source_sentence: term.source_sentence
            }))}
            saved={saved}
            saving={saving}
            onSave={saveItem}
            emptyMessage="No terms found for this section."
          />
        ) : null}
        {activeTab === "phrases" ? (
          <MiniList
            supportLabel={`${supportLanguage ?? "Native"} usage`}
            meaningLabel="Function"
            rows={phrases.map((phrase) => ({
              item_type: "phrase" as const,
              text: normalizeExpressionDisplay(phrase.phrase),
              meaning: stripFiller(phrase.explanation),
              supportMeaning: phrase.support_language_explanation,
              source_sentence: phrase.source_sentence
            }))}
            saved={saved}
            saving={saving}
            onSave={saveItem}
            emptyMessage="No academic phrases found for this section."
          />
        ) : null}
        {activeTab === "patterns" ? (
          sentencePatterns.length ? (
            <div className="space-y-3">
              {sentencePatterns.map((sentence) => {
                const key = `sentence:${sentence.core_structure}`;
                return (
                  <div key={`${sentence.core_structure}:${sentence.sentence}`} className="rounded-md border border-line bg-surface p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1 space-y-2">
                        <p className="text-sm font-semibold text-ink">{sentence.core_structure}</p>
                        <p className="text-sm leading-6 text-neutral-700">{stripFiller(sentence.simplified_version)}</p>
                        {sentence.korean_explanation ? (
                          <p className="text-sm leading-6 text-blue-700">{sentence.korean_explanation}</p>
                        ) : null}
                        {sentence.sentence ? (
                          <p className="border-l-2 border-blue-200 pl-3 text-xs leading-5 text-neutral-500">
                            {truncateText(sentence.sentence, 320)}
                          </p>
                        ) : null}
                      </div>
                      <button
                        type="button"
                        onClick={() =>
                          saveItem({
                            item_type: "sentence",
                            text: sentence.core_structure,
                            meaning: [
                              stripFiller(sentence.simplified_version),
                              sentence.korean_explanation,
                              sentence.difficulty_reason
                            ].filter(Boolean).join(" "),
                            source_sentence: sentence.sentence
                          })
                        }
                        disabled={saved.has(key) || saving === key}
                        className="inline-flex shrink-0 items-center gap-1 rounded-md border border-line bg-panel px-2 py-1.5 text-xs font-semibold text-ink hover:bg-white disabled:text-green-700"
                      >
                        {saved.has(key) ? <CheckCircle2 size={12} /> : <BookmarkPlus size={12} />}
                        {saved.has(key) ? "Saved" : saving === key ? "…" : "Save"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-neutral-500">No sentence patterns found for this section.</p>
          )
        ) : null}
        {activeTab === "ideas" ? (
          concepts.length ? (
            <div className="space-y-3">
              {concepts.map((concept) => {
                const key = `concept:${concept.concept}`;
                const isSaved = saved.has(key);
                const supportMeaning =
                  usefulSupportMeaning(concept.support_language_explanation) ||
                  fallbackSupportMeaning(
                    supportLanguage,
                    "concept",
                    concept.concept,
                    stripFiller(concept.explanation || concept.why_it_matters)
                  );
                const explanation = stripFiller(concept.explanation || concept.why_it_matters);
                return (
                  <div key={concept.concept} className="rounded-md border border-line bg-surface p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-ink">{concept.concept}</p>
                        {supportMeaning ? (
                          <p className="mt-1 text-xs leading-5 text-blue-700">{supportMeaning}</p>
                        ) : null}
                        <p className="mt-1 text-sm leading-5 text-neutral-700">{explanation}</p>
                        {concept.source_sentence ? (
                          <p className="mt-2 border-l-2 border-blue-200 pl-3 text-xs leading-5 text-neutral-500">
                            {truncateText(concept.source_sentence, 200)}
                          </p>
                        ) : null}
                      </div>
                      <button
                        type="button"
                        onClick={() =>
                          saveItem({
                            item_type: "concept",
                            text: concept.concept,
                            meaning: [
                              supportMeaning,
                              explanation
                            ].filter(Boolean).join("\n\n"),
                            source_sentence: concept.source_sentence
                          })
                        }
                        disabled={isSaved || saving === key}
                        className="inline-flex shrink-0 items-center gap-1 rounded-md border border-line bg-panel px-2 py-1.5 text-xs font-semibold text-ink hover:bg-white disabled:text-green-700"
                      >
                        {isSaved ? <CheckCircle2 size={12} /> : <BookmarkPlus size={12} />}
                        {isSaved ? "Saved" : saving === key ? "…" : "Save"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-neutral-500">No key ideas found for this section.</p>
          )
        ) : null}
      </div>
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

export type SectionReaderState = {
  analyzed: boolean;
  sectionNumber: number;
  sectionLabel?: string;
  isBatchAnalyzing: boolean;
};

export type SectionPreparationStatus = {
  message: string;
  mode: "page-batch";
  running: boolean;
  ready: number;
  total: number;
};

function MiniList({
  supportLabel,
  meaningLabel,
  rows,
  saved,
  saving,
  onSave,
  emptyMessage
}: {
  supportLabel: string;
  meaningLabel: string;
  rows: LessonSaveItem[];
  saved: Set<string>;
  saving: string | null;
  onSave: (item: LessonSaveItem) => Promise<void>;
  emptyMessage?: string;
}) {
  return (
    <div>
      {rows.length ? (
        <div className="space-y-2.5">
          {rows.map((row) => {
            const key = `${row.item_type}:${row.text}`;
            const isSaved = saved.has(key);
            const supportMeaning = usefulSupportMeaning(row.supportMeaning);
            return (
            <div key={row.text} className="rounded-md border border-line bg-surface p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-ink">{row.text}</p>
                  {supportMeaning ? (
                    <p className="mt-1 text-xs leading-5 text-blue-700">{supportMeaning}</p>
                  ) : null}
                  <p className="mt-1 text-xs leading-5 text-neutral-600">{row.meaning}</p>
                  {row.source_sentence ? (
                    <p className="mt-2 border-l-2 border-line pl-2.5 text-[11px] leading-4 text-neutral-400">
                      {truncateText(row.source_sentence, 180)}
                    </p>
                  ) : null}
                </div>
                <button
                  type="button"
                  onClick={() => onSave(row)}
                  disabled={isSaved || saving === key}
                  className="inline-flex shrink-0 items-center gap-1 rounded-md border border-line bg-panel px-2 py-1.5 text-xs font-semibold text-ink hover:bg-white disabled:text-green-700"
                >
                  {isSaved ? <CheckCircle2 size={12} /> : <BookmarkPlus size={12} />}
                  {isSaved ? "Saved" : saving === key ? "…" : "Save"}
                </button>
              </div>
            </div>
            );
          })}
        </div>
      ) : (
        <p className="text-sm text-neutral-500">{emptyMessage ?? "No items found."}</p>
      )}
    </div>
  );
}

// Trivially common phrases not worth saving at any level above B1
const BASIC_PHRASE_BLOCKLIST = new Set([
  "based on", "similar to", "similarly to", "in addition to", "as well as", "such as",
  "for example", "for instance", "in order to", "as a result", "in contrast",
  "on the other hand", "due to", "in terms of", "with respect to",
  "with regard to", "consists of", "is based on", "is similar to",
  "can be described as", "is described as", "can be seen as",
  "we propose", "we present", "we describe", "we show", "we find",
  "we use", "we train", "we evaluate", "we compare", "we report",
  "we note", "we define", "we follow", "we replace", "we compute",
  "we employ", "we apply", "we introduce", "we extend", "we adopt",
  "it is", "it can be", "this is", "there are", "there is",
  "can be used", "is used to", "is used for", "is defined as",
  "as shown in", "as described in", "as discussed in",
  "in this paper", "in this work", "in this section",
  "in the following", "in the next section",
]);

function isUsefulExpression(value: string) {
  const normalized = value.trim().toLowerCase();
  const words = normalized.split(/\s+/).filter(Boolean);
  if (!normalized) return false;
  if (BASIC_PHRASE_BLOCKLIST.has(normalized)) return false;
  if (words.length < 2) return false;
  if (/^\d/.test(normalized)) return false;
  // Benchmark/dataset names without context
  if (/\b(wmt|bleu|gpu|p100|imagenet|mnist)\b/i.test(value) && words.length <= 4) return false;
  // Single pronoun + single common verb (e.g. "We employ", "We use")
  if (/^(we|i|they|it|the model|our model|this model)\s+\w+$/i.test(value.trim())) return false;
  if (/^[a-z]+\s+(the|a|an)$/i.test(value.trim())) return false;
  // Surface clauses: long phrases that are verbatim text extracts (contain embedded formulas or specific numbers)
  if (words.length > 6 && /\b(n\s*=\s*\d|positions|attending to|composed of a stack)\b/i.test(value)) return false;
  return true;
}

// Strip leading pronoun subject from short phrases for display ("We employ" → "employ")
function normalizeExpressionDisplay(value: string): string {
  return value
    .replace(/^(We|I|They|It|The model|Our model|This model)\s+(?=[a-z])/i, "")
    .trim();
}

function normalizeItemText(value: string) {
  return value.trim().toLowerCase().replace(/\s+/g, " ");
}

function dedupeByText<T>(rows: T[], getText: (row: T) => string) {
  const seen = new Set<string>();
  return rows.filter((row) => {
    const key = normalizeItemText(getText(row));
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
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

function findParentSectionIndex(sections: DocumentSection[], continuationIndex: number): number | null {
  const currentPage = pdfPageFromLabel(sections[continuationIndex]?.source_label ?? null);
  for (let i = continuationIndex - 1; i >= 0; i--) {
    const page = pdfPageFromLabel(sections[i]?.source_label ?? null);
    if (page !== currentPage) return i;
  }
  return null;
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
    group.label = pdfPage ? `Page ${pdfPage}` : "Page unknown";
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

function findAdjacentPdfPageIndex(sections: DocumentSection[], currentIndex: number, direction: -1 | 1) {
  const currentPage = pdfPageFromLabel(sections[currentIndex]?.source_label ?? null);
  if (!currentPage) return null;
  if (direction < 0) {
    for (let cursor = currentIndex - 1; cursor >= 0; cursor -= 1) {
      const page = pdfPageFromLabel(sections[cursor]?.source_label ?? null);
      if (page && page !== currentPage) {
        while (cursor > 0 && pdfPageFromLabel(sections[cursor - 1]?.source_label ?? null) === page) {
          cursor -= 1;
        }
        return cursor;
      }
    }
    return null;
  }
  for (let cursor = currentIndex + 1; cursor < sections.length; cursor += 1) {
    const page = pdfPageFromLabel(sections[cursor]?.source_label ?? null);
    if (page && page !== currentPage) return cursor;
  }
  return null;
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
  const title = formatSectionTitle(section);
  const pageLabel = pdfPage ? `Page ${pdfPage}` : "Page unknown";
  const localLabel = localSection ? `Part ${localSection}` : "part unknown";
  const globalLabel = global && total ? `${global} / ${total} lessons` : "lesson unknown";
  return title ? `${title} · ${pageLabel} · ${localLabel} · ${globalLabel}` : `${pageLabel} · ${localLabel} · ${globalLabel}`;
}

function formatSectionTitle(section: DocumentSection | undefined) {
  const title = section?.title?.trim();
  if (!title) return "";
  return section?.continuation ? `${title} (continued)` : title;
}

function compactSectionNavLabel(section: DocumentSection, localNumber: number) {
  return `${localNumber}`;
}

function stripFiller(text: string | undefined): string | undefined {
  if (!text) return text;
  return text
    .replace(/^(This term refers to|This term means|The term refers to|The term means)\s+/i, "")
    .replace(/^(In this context,?\s*)/i, "")
    .replace(/^(This section (discusses|explains|covers|introduces|describes|examines|presents|focuses on)\s*)/i, "")
    .replace(/^(In this sentence,?\s*)/i, "")
    .replace(/^(This expression is used to\s*)/i, "")
    .replace(/^(In academic writing,?\s*)/i, "")
    .replace(/^(This phrase (is used to|means|refers to|indicates)\s*)/i, "")
    .replace(/^(This (pattern|structure) (is used to|shows|indicates|means)\s*)/i, "")
    .trim();
}

function usefulSupportMeaning(value: string | undefined) {
  const normalized = value?.trim();
  if (!normalized) return null;
  if (
    normalized.includes("새로 분석하면 더 구체적인 한국어 gloss") ||
    normalized.includes("새로 분석하면 더 구체적인 한국어")
  ) {
    return null;
  }
  if (!/[가-힣]/.test(normalized) && normalized.length > 60) return null;
  return normalized;
}

function fallbackSupportMeaning(language: string | undefined, kind: "term" | "phrase" | "concept", text: string, meaning: string | undefined) {
  const normalizedLanguage = language?.trim().toLowerCase();
  const normalizedMeaning = meaning?.trim();
  if (!normalizedMeaning) return null;
  if (normalizedLanguage && !["korean", "ko", "한국어"].includes(normalizedLanguage)) return null;
  if (/[가-힣]/.test(normalizedMeaning)) return normalizedMeaning;
  if (kind === "term") return `문맥상 의미: ${normalizedMeaning}`;
  if (kind === "concept") return `핵심 개념: ${normalizedMeaning}`;
  return `문맥상 기능: ${normalizedMeaning}`;
}

function nextUnanalyzedPageNumbers(sections: DocumentSection[], limit: number) {
  const pages: number[] = [];
  const seen = new Set<number>();
  sections.forEach((section, index) => {
    if (section.analyzed) return;
    const page = pdfPageFromLabel(section.source_label) ?? (index === 0 ? 1 : null);
    if (!page || seen.has(page)) return;
    seen.add(page);
    pages.push(page);
  });
  return pages.slice(0, limit);
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
