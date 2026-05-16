"use client";

import { BookmarkPlus, CheckCircle2, ChevronLeft, ChevronRight, Eye, EyeOff, Paperclip, ScanText, SkipForward } from "lucide-react";
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
  const sectionGroups = groupSectionsByPdfPage(sections);
  const currentPdfPage = pdfPageFromLabel(currentSection?.source_label ?? null);
  const currentPageSectionNumber = currentSection ? sectionNumberWithinPdfPage(sections, pageIndex) : null;

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
    onSourcePageChange?.(currentPdfPage);
  }, [currentPdfPage, onSourcePageChange]);

  useEffect(() => {
    if (!requestedSourcePage || !sections.length) return;
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
          <h2 className="mt-1 text-lg font-semibold">Move through PDF pages and text sections</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-neutral-600">
            PDF pages are the visual source on the left. Sections are backend-cleaned text chunks sent to the model; one PDF page can contain several sections.
          </p>
          <p className="mt-2 text-xs font-semibold text-neutral-600">
            {analyzedCount} / {sections.length || 1} sections analyzed
          </p>
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 lg:w-auto lg:justify-end">
          <button
            type="button"
            onClick={goToNextUnanalyzed}
            disabled={targetUnanalyzedIndex < 0 || isBatchAnalyzing}
            className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-semibold text-ink hover:bg-surface disabled:opacity-40"
          >
            <SkipForward size={16} />
            Next unstudied
          </button>
          <button
            type="button"
            onClick={autoStudyNextSections}
            disabled={!plannedBatchIndices.length || isBatchAnalyzing || isAnalyzing}
            className="inline-flex items-center gap-2 rounded-md border border-line bg-panel px-3 py-2 text-sm font-semibold text-ink hover:bg-surface disabled:opacity-40"
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
            disabled={isAnalyzing || isBatchAnalyzing || !currentSection || !page.trim()}
            className="inline-flex items-center gap-2 rounded-md bg-accent px-3 py-2 text-sm font-semibold text-white disabled:bg-neutral-300 disabled:text-neutral-600"
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
        <div className="flex gap-3 overflow-x-auto border-b border-line px-5 py-3">
          {sectionGroups.map((group) => (
            <div key={group.key} className="shrink-0 rounded-md border border-line bg-surface p-2">
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-neutral-500">{group.label}</p>
              <div className="flex gap-1">
                {group.items.map(({ section, index, localNumber }) => (
                  <button
                    key={section.index}
                    type="button"
                    onClick={() => setPageIndex(index)}
                    className={`flex h-8 min-w-12 items-center justify-center rounded-md border px-2 text-[11px] font-semibold ${
                      index === pageIndex
                        ? "border-accent bg-accent text-white"
                        : section.analyzed
                          ? "border-green-200 bg-green-50 text-green-700"
                          : "border-line bg-panel text-neutral-500 hover:bg-white"
                    }`}
                    title={`${group.label}, section ${localNumber} on this page, document section ${section.section_number}${
                      section.analyzed ? " analyzed" : " not analyzed"
                    }`}
                  >
                    <span>P{group.pdfPage ?? "?"}-S{localNumber}</span>
                    {section.analyzed && index !== pageIndex ? <CheckCircle2 size={12} className="ml-1" /> : null}
                  </button>
                ))}
              </div>
            </div>
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
            Document section {currentSection?.section_number ?? pageIndex + 1} / {currentSection?.total_sections ?? Math.max(sections.length, 1)}
          </p>
          <p className="text-xs font-semibold text-neutral-600">
            {currentPdfPage ? `PDF page ${currentPdfPage}` : "PDF page unknown"}
            {currentPageSectionNumber ? ` · section P${currentPdfPage ?? "?"}-S${currentPageSectionNumber} on this page` : ""}
          </p>
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
          embedded
        />
      ) : null}
    </section>
  );
}

export function SectionLessonCard({
  analysis,
  sectionNumber,
  onAnalyzeNext,
  isAnalyzingNext,
  embedded = false
}: {
  analysis: AnalysisResult;
  sectionNumber: number;
  onAnalyzeNext?: () => void;
  isAnalyzingNext: boolean;
  embedded?: boolean;
}) {
  const [saved, setSaved] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState<string | null>(null);
  const concepts = (analysis.concepts ?? []).slice(0, 6);
  const terms = analysis.terms.slice(0, 8);
  const phrases = analysis.phrases.filter((phrase) => isUsefulExpression(phrase.phrase)).slice(0, 6);
  const studyNotes = analysis.summaries.study_notes.slice(0, 4);
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
          <h3 className="mt-1 text-lg font-semibold">{analysis.summaries.one_line}</h3>
        </div>
        <p className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-accent">
          {concepts.length} concepts · {terms.length} terms · {phrases.length} expressions
        </p>
      </div>
      <p className="mt-2 text-sm leading-6 text-neutral-700">{analysis.summaries.simple}</p>
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
      <div className="mt-5 grid gap-4">
        <MiniList
          title="Terms to save if unfamiliar"
          rows={terms.map((term) => ({
            item_type: "term" as const,
            text: term.term,
            meaning: term.meaning,
            source_sentence: term.source_sentence
          }))}
          saved={saved}
          saving={saving}
          onSave={saveItem}
        />
        <MiniList
          title="Reusable academic expressions"
          rows={phrases.map((phrase) => ({
            item_type: "phrase" as const,
            text: phrase.phrase,
            meaning: phrase.explanation,
            source_sentence: phrase.source_sentence
          }))}
          saved={saved}
          saving={saving}
          onSave={saveItem}
        />
      </div>
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

type LessonSaveItem = {
  item_type: "term" | "phrase" | "sentence" | "concept";
  text: string;
  meaning?: string;
  source_sentence?: string;
};

function MiniList({
  title,
  rows,
  saved,
  saving,
  onSave
}: {
  title: string;
  rows: LessonSaveItem[];
  saved: Set<string>;
  saving: string | null;
  onSave: (item: LessonSaveItem) => Promise<void>;
}) {
  return (
    <div className="rounded-md border border-line bg-surface p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{title}</p>
      {rows.length ? (
        <div className="mt-3 space-y-3">
          {rows.map((row) => {
            const key = `${row.item_type}:${row.text}`;
            const isSaved = saved.has(key);
            return (
            <div key={row.text} className="flex items-start justify-between gap-3 border-t border-line pt-3 first:border-t-0 first:pt-0">
              <div>
                <p className="text-sm font-semibold text-ink">{row.text}</p>
                <p className="mt-1 text-xs leading-5 text-neutral-600">{row.meaning}</p>
                {row.source_sentence ? <p className="mt-1 text-xs leading-5 text-neutral-500">{truncateText(row.source_sentence, 220)}</p> : null}
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
  const normalized = value.split(/\s+/).join(" ");
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
    const sectionCount = group.items.length;
    group.label = pdfPage ? `PDF page ${pdfPage} · S1-S${sectionCount}` : `PDF page unknown · S1-S${sectionCount}`;
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
