"use client";

import { RefreshCw, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import type { AnalysisResult, DocumentListItem } from "@/lib/types";

type Source = { document: DocumentListItem; analysis: AnalysisResult };
type QuizItem = { prompt: string; answer: string; source: string; type: "term" | "phrase" | "sentence" };

const CACHE_PREFIX = "gemmalens.quiz.";

export default function QuizPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [items, setItems] = useState<QuizItem[]>([]);
  const [status, setStatus] = useState("Loading analyzed sources...");

  useEffect(() => {
    let cancelled = false;
    async function loadSources() {
      try {
        const documents = await api.listDocuments();
        const settled = await Promise.allSettled(
          documents.map(async (document) => ({ document, analysis: await api.getAnalysis(document.id) }))
        );
        const ready = settled.flatMap((entry) => (entry.status === "fulfilled" ? [entry.value] : []));
        if (cancelled) return;
        setSources(ready);
        setSelectedId(ready[0]?.document.id ?? "");
        setStatus(ready.length ? "Choose an analyzed document or transcript." : "No analyzed sources yet.");
      } catch (err) {
        if (!cancelled) setStatus(err instanceof Error ? err.message : "Could not load analyzed sources.");
      }
    }
    loadSources();
    return () => {
      cancelled = true;
    };
  }, []);

  const selected = useMemo(() => sources.find((source) => source.document.id === selectedId), [selectedId, sources]);

  useEffect(() => {
    if (!selected) {
      setItems([]);
      return;
    }
    const cached = window.localStorage.getItem(CACHE_PREFIX + selected.document.id);
    setItems(cached ? JSON.parse(cached) : buildQuiz(selected.analysis));
  }, [selected]);

  function regenerate() {
    if (!selected) return;
    const next = buildQuiz(selected.analysis).sort(() => Math.random() - 0.5);
    setItems(next);
  }

  function cacheQuiz() {
    if (!selected) return;
    window.localStorage.setItem(CACHE_PREFIX + selected.document.id, JSON.stringify(items));
    setStatus(`Cached ${items.length} quiz items for ${selected.document.title}.`);
  }

  return (
    <AppShell>
      <div className="mb-6">
        <p className="text-sm font-semibold uppercase text-accent">Experimental</p>
        <h1 className="mt-2 text-2xl font-semibold">Quiz maker</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-600">
          Build review prompts from analyzed documents and video transcripts. Drafts are cached in this browser.
        </p>
      </div>
      <section className="grid gap-5 lg:grid-cols-[360px_minmax(0,1fr)]">
        <aside className="rounded-lg border border-line bg-panel p-5 shadow-material">
          <h2 className="font-semibold">Analyzed sources</h2>
          <p className="mt-2 text-sm leading-6 text-neutral-600">{status}</p>
          <div className="mt-4 space-y-2">
            {sources.map(({ document }) => (
              <button
                key={document.id}
                type="button"
                onClick={() => setSelectedId(document.id)}
                className={`w-full rounded-md border p-3 text-left text-sm ${
                  selectedId === document.id ? "border-accent bg-blue-50 text-ink" : "border-line hover:bg-surface"
                }`}
              >
                <span className="block font-semibold">{document.title}</span>
                <span className="mt-1 block text-xs uppercase text-neutral-500">{document.source_type}</span>
              </button>
            ))}
          </div>
        </aside>
        <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold">{selected?.document.title ?? "No source selected"}</h2>
              <p className="mt-1 text-sm text-neutral-600">{items.length} draft quiz items</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={regenerate} disabled={!selected} className="inline-flex items-center gap-2 rounded-md border border-line px-4 py-2 text-sm font-semibold hover:bg-surface disabled:opacity-50">
                <RefreshCw size={16} />
                Regenerate
              </button>
              <button type="button" onClick={cacheQuiz} disabled={!selected || !items.length} className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:bg-neutral-300 disabled:text-neutral-600">
                <Save size={16} />
                Cache
              </button>
            </div>
          </div>
          <div className="mt-5 space-y-3">
            {items.map((item, index) => (
              <details key={`${item.type}-${item.prompt}-${index}`} className="rounded-lg border border-line bg-surface p-4 text-sm">
                <summary className="cursor-pointer font-semibold">Q{index + 1}. {item.prompt}</summary>
                <p className="mt-3 leading-6 text-neutral-800">{item.answer}</p>
                <p className="mt-2 text-xs text-neutral-500">{item.source}</p>
              </details>
            ))}
          </div>
        </div>
      </section>
    </AppShell>
  );
}

function buildQuiz(analysis: AnalysisResult): QuizItem[] {
  return [
    ...analysis.terms.slice(0, 8).map((term): QuizItem => ({
      type: "term",
      prompt: `What does "${term.term}" mean here?`,
      answer: term.meaning,
      source: term.source_sentence
    })),
    ...analysis.phrases.slice(0, 5).map((phrase): QuizItem => ({
      type: "phrase",
      prompt: `What function does "${phrase.phrase}" serve?`,
      answer: phrase.explanation,
      source: phrase.source_sentence
    })),
    ...analysis.sentences.slice(0, 4).map((sentence): QuizItem => ({
      type: "sentence",
      prompt: "Simplify this sentence structure.",
      answer: `${sentence.core_structure}\n${sentence.simplified_version}`,
      source: sentence.sentence
    }))
  ];
}
