"use client";

import { ChevronLeft, ChevronRight, Eye, EyeOff, Paperclip, ScanText } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { AnalysisResult, DocumentRead, DocumentSection } from "@/lib/types";

export function DocumentPageReader({ documentId, onSectionAnalyzed }: { documentId: string; onSectionAnalyzed?: () => void }) {
  const [document, setDocument] = useState<DocumentRead | null>(null);
  const [sections, setSections] = useState<DocumentSection[]>([]);
  const [pageIndex, setPageIndex] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isAttaching, setIsAttaching] = useState(false);
  const [sectionAnalysis, setSectionAnalysis] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState("");
  const attachInputRef = useRef<HTMLInputElement>(null);
  const currentSection = sections[pageIndex];
  const page = currentSection?.text ?? "";

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
    setError("");
  }, [pageIndex]);

  async function analyzePage() {
    if (!document || !currentSection || !page.trim()) return;
    setIsAnalyzing(true);
    setError("");
    try {
      const created = await api.analyzeDocumentSection(document.id, currentSection.index);
      setSectionAnalysis(created);
      onSectionAnalyzed?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not analyze this section.");
    } finally {
      setIsAnalyzing(false);
    }
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

  return (
    <section className="rounded-lg border border-line bg-panel shadow-material">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line p-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Section study</p>
          <h2 className="mt-1 text-lg font-semibold">Move through extracted sections</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-neutral-600">
            Use this when the whole document is too long for one edge-model pass. These are model-input text sections, not rendered PDF pages.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
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
            disabled={isAnalyzing || !currentSection || !page.trim()}
            className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:bg-neutral-300 disabled:text-neutral-600"
          >
            <ScanText size={16} />
            {isAnalyzing ? "Analyzing section..." : "Analyze this section"}
          </button>
        </div>
      </div>
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
          <p className="text-xs text-neutral-500">{(currentSection?.char_count ?? page.length).toLocaleString()} chars from backend-cleaned text</p>
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
        <p className="max-w-2xl text-xs leading-5 text-neutral-600">
          The left PDF is the visual source. This section text is what the model can read; it may lose equations, columns, or line breaks.
        </p>
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
      {sectionAnalysis ? <InlineSectionLesson analysis={sectionAnalysis} sectionNumber={pageIndex + 1} /> : null}
    </section>
  );
}

function InlineSectionLesson({ analysis, sectionNumber }: { analysis: AnalysisResult; sectionNumber: number }) {
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
      <div className="mt-5 grid gap-4 md:grid-cols-2">
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
