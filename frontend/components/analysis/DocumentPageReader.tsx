"use client";

import { ChevronLeft, ChevronRight, ScanText } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { DocumentRead } from "@/lib/types";

const PAGE_CHARS = 1800;

export function DocumentPageReader({ documentId }: { documentId: string }) {
  const [document, setDocument] = useState<DocumentRead | null>(null);
  const [pageIndex, setPageIndex] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const pages = useMemo(() => splitPages(document?.content ?? ""), [document?.content]);
  const page = pages[pageIndex] ?? "";

  useEffect(() => {
    let cancelled = false;
    api
      .getDocument(documentId)
      .then((loaded) => {
        if (!cancelled) setDocument(loaded);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load the source document reader.");
      });
    return () => {
      cancelled = true;
    };
  }, [documentId]);

  async function analyzePage() {
    if (!document || !page.trim()) return;
    setIsAnalyzing(true);
    setError("");
    try {
      const created = await api.createDocument({
        title: `${document.title} · page ${pageIndex + 1}`,
        source_type: document.source_type,
        content: page
      });
      await api.analyzeDocument(created.id);
      window.location.href = `/analysis/${created.id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not analyze this page.");
      setIsAnalyzing(false);
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
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line p-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Reader</p>
          <h2 className="mt-1 text-lg font-semibold">Read and analyze page by page</h2>
          <p className="mt-1 text-sm text-neutral-600">Use this when the full paper is too long for one edge-model pass.</p>
        </div>
        <button
          type="button"
          onClick={analyzePage}
          disabled={isAnalyzing || !page.trim()}
          className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:bg-neutral-300 disabled:text-neutral-600"
        >
          <ScanText size={16} />
          {isAnalyzing ? "Analyzing page..." : "Analyze this page"}
        </button>
      </div>
      <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-3">
        <button
          type="button"
          onClick={() => setPageIndex((value) => Math.max(0, value - 1))}
          disabled={pageIndex === 0}
          className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-xs font-semibold text-ink hover:bg-surface disabled:opacity-40"
        >
          <ChevronLeft size={15} />
          Previous
        </button>
        <p className="text-sm font-semibold text-neutral-600">
          Page slice {pageIndex + 1} / {Math.max(pages.length, 1)}
        </p>
        <button
          type="button"
          onClick={() => setPageIndex((value) => Math.min(pages.length - 1, value + 1))}
          disabled={pageIndex >= pages.length - 1}
          className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-xs font-semibold text-ink hover:bg-surface disabled:opacity-40"
        >
          Next
          <ChevronRight size={15} />
        </button>
      </div>
      {error ? <p className="mx-5 mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
      <article className="max-h-[520px] overflow-y-auto whitespace-pre-wrap p-5 text-sm leading-7 text-neutral-800">{page}</article>
    </section>
  );
}

function splitPages(text: string) {
  const cleaned = text
    .replace(/\r\n/g, "\n")
    .replace(/([A-Za-z]{3,})-\s+([a-z]{2,})/g, "$1$2")
    .replace(/([A-Za-z]{3,})-\s*\n\s*([a-z]{2,})/g, "$1$2")
    .replace(/\b(?:tion|sion|ment|sentation|resentation|pre)\s+(?:model|models|network|networks|training|representations)\b/gi, "")
    .replace(/[ \t]+/g, " ")
    .trim();
  if (!cleaned) return [];
  const sentences = cleaned.split(/(?<=[.!?])\s+/);
  const pages: string[] = [];
  let current = "";
  for (const sentence of sentences) {
    if (current.length + sentence.length > PAGE_CHARS && current) {
      pages.push(current.trim());
      current = sentence;
    } else {
      current = `${current} ${sentence}`.trim();
    }
  }
  if (current) pages.push(current.trim());
  return pages;
}
