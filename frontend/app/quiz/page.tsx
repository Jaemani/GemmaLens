"use client";

import { RefreshCw, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import { cleanDocumentPreview, displayableDocuments } from "@/lib/documentDisplay";
import type { AnalysisResult, DictionaryItem, DocumentListItem, PaperMap } from "@/lib/types";

type Source = { document: DocumentListItem; analysis: AnalysisResult | null; paperMap: PaperMap | null };
type QuizItem = {
  prompt: string;
  answer: string;
  source: string;
  type: "concept" | "term" | "phrase" | "sentence";
  dictionaryItemId?: string;
};

const CACHE_PREFIX = "gemmalens.quiz.";
const DICTIONARY_SOURCE_ID = "__dictionary__";

export default function QuizPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [dictionaryItems, setDictionaryItems] = useState<DictionaryItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [items, setItems] = useState<QuizItem[]>([]);
  const [viewedDictionaryItems, setViewedDictionaryItems] = useState<Set<string>>(new Set());
  const [status, setStatus] = useState("Loading analyzed sources...");

  useEffect(() => {
    let cancelled = false;
    async function loadSources() {
      try {
        const [documentsRaw, dictionary] = await Promise.all([api.listDocuments(), api.listDictionary().catch(() => [])]);
        const documents = displayableDocuments(documentsRaw.filter((document) => document.has_analysis || (document.analyzed_sections ?? 0) > 0));
        const settled = await Promise.allSettled(
          documents.map(async (document) => {
            const [analysis, paperMap] = await Promise.all([
              document.has_analysis ? api.getAnalysis(document.id).catch(() => null) : Promise.resolve(null),
              (document.analyzed_sections ?? 0) > 0 ? api.getPaperMap(document.id).catch(() => null) : Promise.resolve(null)
            ]);
            return { document, analysis, paperMap };
          })
        );
        const ready = settled.flatMap((entry) => (entry.status === "fulfilled" ? [entry.value] : []));
        if (cancelled) return;
        setSources(ready);
        setDictionaryItems(dictionary);
        setSelectedId(dictionary.length ? DICTIONARY_SOURCE_ID : (ready[0]?.document.id ?? ""));
        setStatus(ready.length || dictionary.length ? "Choose saved items, an analyzed document, or a transcript." : "No analyzed sources yet.");
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
  const selectedDictionary = selectedId === DICTIONARY_SOURCE_ID;

  useEffect(() => {
    if (selectedDictionary) {
      const cached = window.localStorage.getItem(CACHE_PREFIX + DICTIONARY_SOURCE_ID);
      setItems(cached ? JSON.parse(cached) : buildDictionaryQuiz(dictionaryItems));
      return;
    }
    if (!selected) {
      setItems([]);
      return;
    }
    const cached = window.localStorage.getItem(CACHE_PREFIX + selected.document.id);
    setItems(cached ? JSON.parse(cached) : buildQuiz(selected));
  }, [dictionaryItems, selected, selectedDictionary]);

  function regenerate() {
    if (!selected && !selectedDictionary) return;
    const next = (selectedDictionary ? buildDictionaryQuiz(dictionaryItems) : buildQuiz(selected!)).sort(() => Math.random() - 0.5);
    setItems(next);
  }

  function cacheQuiz() {
    if (!selected && !selectedDictionary) return;
    const key = selectedDictionary ? DICTIONARY_SOURCE_ID : selected!.document.id;
    const title = selectedDictionary ? "Saved dictionary" : selected!.document.title;
    window.localStorage.setItem(CACHE_PREFIX + key, JSON.stringify(items));
    setStatus(`Cached ${items.length} quiz items for ${title}.`);
  }

  async function markQuizItemViewed(item: QuizItem, open: boolean) {
    if (!open || !item.dictionaryItemId || viewedDictionaryItems.has(item.dictionaryItemId)) return;
    setViewedDictionaryItems((previous) => new Set(previous).add(item.dictionaryItemId!));
    try {
      await api.markDictionaryViewed(item.dictionaryItemId);
    } catch {
      setViewedDictionaryItems((previous) => {
        const next = new Set(previous);
        next.delete(item.dictionaryItemId!);
        return next;
      });
    }
  }

  const selectedTitle = selectedDictionary ? "Saved dictionary" : (selected?.document.title ?? "No source selected");

  return (
    <AppShell>
      <div className="w-full">
        <div className="mb-5">
          <h1 className="text-2xl font-semibold">Review quiz</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-600">
            Build quick review prompts from analyzed sources. This is a lightweight practice layer; the document reader remains the main paper-learning workspace.
          </p>
        </div>
        <section className="grid gap-5 lg:grid-cols-[360px_minmax(0,1fr)]">
          <aside className="rounded-lg border border-line bg-panel p-5 shadow-material">
          <h2 className="font-semibold">Analyzed sources</h2>
          <p className="mt-2 text-sm leading-6 text-neutral-600">{status}</p>
          <div className="mt-4 space-y-2">
            {dictionaryItems.length ? (
              <button
                type="button"
                onClick={() => setSelectedId(DICTIONARY_SOURCE_ID)}
                className={`w-full rounded-md border p-3 text-left text-sm ${
                  selectedDictionary ? "border-accent bg-blue-50 text-ink" : "border-line hover:bg-surface"
                }`}
              >
                <span className="block font-semibold">Saved dictionary</span>
                <span className="mt-1 block text-xs uppercase text-neutral-500">{dictionaryItems.length} saved study items</span>
                <span className="mt-2 line-clamp-2 block text-xs leading-5 text-neutral-600">
                  Review concepts, terms, expressions, and sentence patterns you saved while reading.
                </span>
              </button>
            ) : null}
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
                <span className="mt-2 line-clamp-2 block text-xs leading-5 text-neutral-600">{cleanDocumentPreview(document)}</span>
              </button>
            ))}
          </div>
          </aside>
          <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold">{selectedTitle}</h2>
              <p className="mt-1 text-sm text-neutral-600">{items.length} review prompts from this source</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={regenerate} disabled={!selected && !selectedDictionary} className="inline-flex items-center gap-2 rounded-md border border-line px-4 py-2 text-sm font-semibold hover:bg-surface disabled:opacity-50">
                <RefreshCw size={16} />
                Regenerate
              </button>
              <button type="button" onClick={cacheQuiz} disabled={(!selected && !selectedDictionary) || !items.length} className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:bg-neutral-300 disabled:text-neutral-600">
                <Save size={16} />
                Save draft
              </button>
            </div>
          </div>
          <div className="mt-5 space-y-3">
            {items.length ? items.map((item, index) => (
              <details
                key={`${item.type}-${item.prompt}-${index}`}
                onToggle={(event) => {
                  void markQuizItemViewed(item, event.currentTarget.open);
                }}
                className="rounded-lg border border-line bg-surface p-4 text-sm"
              >
                <summary className="cursor-pointer font-semibold">Q{index + 1}. {item.prompt}</summary>
                <p className="mt-3 leading-6 text-neutral-800">{item.answer}</p>
                <p className="mt-2 text-xs text-neutral-500">{item.source}</p>
              </details>
            )) : (
              <div className="rounded-lg border border-dashed border-line bg-surface p-6 text-sm leading-6 text-neutral-600">
                Analyze a document first, then return here to generate review prompts.
              </div>
            )}
          </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function buildDictionaryQuiz(items: DictionaryItem[]): QuizItem[] {
  return items.slice(0, 24).map((item): QuizItem => {
    if (item.item_type === "concept") {
      return {
        type: "concept",
        prompt: `Why does "${item.text}" matter?`,
        answer: item.meaning || "Review the source evidence where you saved this concept.",
        source: item.source_sentence || "Saved dictionary item",
        dictionaryItemId: item.id
      };
    }
    if (item.item_type === "phrase") {
      return {
        type: "phrase",
        prompt: `What academic move does "${item.text}" make?`,
        answer: item.meaning || "Explain how this expression works in the source sentence.",
        source: item.source_sentence || "Saved dictionary item",
        dictionaryItemId: item.id
      };
    }
    if (item.item_type === "sentence") {
      return {
        type: "sentence",
        prompt: "Simplify this saved sentence pattern.",
        answer: item.meaning || item.text,
        source: item.source_sentence || item.text,
        dictionaryItemId: item.id
      };
    }
    return {
      type: "term",
      prompt: `What does "${item.text}" mean in context?`,
      answer: item.meaning || "Review the source sentence and define this term in your own words.",
      source: item.source_sentence || "Saved dictionary item",
      dictionaryItemId: item.id
    };
  });
}

function buildQuiz(source: Source): QuizItem[] {
  const mapItems = source.paperMap ? buildPaperMapQuiz(source.paperMap) : [];
  const analysisItems = source.analysis ? buildAnalysisQuiz(source.analysis) : [];
  return [...mapItems, ...analysisItems].slice(0, 18);
}

function buildPaperMapQuiz(paperMap: PaperMap): QuizItem[] {
  const synthesis = paperMap.synthesis;
  if (!synthesis) return [];
  return [
    ...synthesis.priority_concepts.slice(0, 6).map((concept): QuizItem => ({
      type: "concept",
      prompt: `Why does "${concept.text}" matter in this paper?`,
      answer: concept.meaning,
      source: `Paper sections: ${concept.sections.map((section) => `S${section}`).join(", ")}`
    })),
    ...synthesis.priority_terms.slice(0, 6).map((term): QuizItem => ({
      type: "term",
      prompt: `What does "${term.text}" mean in this paper?`,
      answer: term.meaning,
      source: `Paper sections: ${term.sections.map((section) => `S${section}`).join(", ")}`
    })),
    ...synthesis.reusable_expressions.slice(0, 4).map((phrase): QuizItem => ({
      type: "phrase",
      prompt: `What academic move does "${phrase.text}" make?`,
      answer: phrase.meaning,
      source: `Paper sections: ${phrase.sections.map((section) => `S${section}`).join(", ")}`
    }))
  ];
}

function buildAnalysisQuiz(analysis: AnalysisResult): QuizItem[] {
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
