"use client";

import { Clipboard, Languages, Loader2, RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";
import { LanguageSelect } from "@/components/common/LanguageSelect";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";

const LIMIT = 1200;

export default function TranslatePage() {
  const [sourceLanguage, setSourceLanguage] = useState("English");
  const [targetLanguage, setTargetLanguage] = useState("Korean");
  const [text, setText] = useState("");
  const [result, setResult] = useState("");
  const [notes, setNotes] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [isTranslating, setIsTranslating] = useState(false);
  const [copied, setCopied] = useState(false);
  const clipped = text.slice(0, LIMIT);
  const sentenceCount = useMemo(() => clipped.split(/[.!?\n]/).filter((line) => line.trim()).length, [clipped]);

  async function translate() {
    if (!clipped.trim()) return;
    setIsTranslating(true);
    setError("");
    setResult("");
    setNotes([]);
    try {
      const response = await api.translateText({
        source_language: sourceLanguage,
        target_language: targetLanguage,
        text: clipped
      });
      setResult(response.translated_text);
      setNotes(response.notes);
      setCopied(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Translation failed.");
    } finally {
      setIsTranslating(false);
    }
  }

  async function copyResult() {
    if (!result) return;
    await navigator.clipboard.writeText(result);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  function reset() {
    setText("");
    setResult("");
    setNotes([]);
    setError("");
    setCopied(false);
  }

  return (
    <AppShell>
      <div className="w-full">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="mt-2 text-2xl font-semibold">Translate</h1>
            <p className="mt-2 text-sm text-neutral-600">Quick model-backed translation for short sentences and paragraphs.</p>
          </div>
          <p className="text-xs font-medium text-neutral-500">{LIMIT} character limit</p>
        </div>
        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px]">
          <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
            <div className="grid gap-3 sm:grid-cols-2">
              <LanguageSelect label="From" value={sourceLanguage} onChange={setSourceLanguage} />
              <LanguageSelect label="To" value={targetLanguage} onChange={setTargetLanguage} />
            </div>
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value.slice(0, LIMIT))}
              rows={12}
              placeholder="Paste a sentence or short paragraph."
              className="mt-5 w-full resize-y rounded-md border border-line px-3 py-2 text-sm leading-6"
            />
            <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs font-medium text-neutral-500">
                {clipped.length}/{LIMIT} chars · {sentenceCount} segments
              </p>
              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={reset} className="inline-flex items-center gap-2 rounded-md border border-line px-4 py-2 text-sm font-semibold text-ink hover:bg-surface">
                  <RotateCcw size={16} />
                  Clear
                </button>
                <button
                  type="button"
                  onClick={translate}
                  disabled={!clipped.trim() || isTranslating}
                  className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:bg-neutral-300 disabled:text-neutral-600"
                >
                  {isTranslating ? <Loader2 size={16} className="animate-spin" /> : <Languages size={16} />}
                  {isTranslating ? "Translating..." : "Translate"}
                </button>
              </div>
            </div>
            {error ? (
              <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </div>
            ) : null}
          </div>
          <aside className="rounded-lg border border-line bg-panel p-5 shadow-material">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-semibold">Result</h2>
              <button
                type="button"
                onClick={copyResult}
                disabled={!result}
                className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-xs font-semibold text-ink hover:bg-surface disabled:opacity-50"
              >
                <Clipboard size={14} />
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <div className="mt-4 min-h-64 rounded-md bg-surface p-4">
              {isTranslating ? (
                <div className="flex h-56 flex-col items-center justify-center text-center text-sm text-neutral-600">
                  <Loader2 size={22} className="mb-3 animate-spin text-accent" />
                  <p className="font-semibold text-ink">Running local translation</p>
                  <p className="mt-1 max-w-xs leading-6">Short inputs usually finish faster. Larger edge models can take longer on CPU-only hosts.</p>
                </div>
              ) : result ? (
                <pre className="whitespace-pre-wrap text-sm leading-6 text-neutral-800">{result}</pre>
              ) : (
                <div className="flex h-56 flex-col justify-center rounded-md border border-dashed border-line px-4 text-sm leading-6 text-neutral-600">
                  <p className="font-semibold text-ink">No translation yet</p>
                  <p className="mt-1">Use this for quick sentence support while reading. Full papers should stay in the document reader so terms, concepts, and expressions remain source-grounded.</p>
                </div>
              )}
            </div>
            {notes.length ? (
              <div className="mt-4 space-y-2">
                <h3 className="text-xs font-semibold uppercase text-neutral-500">Learner notes</h3>
                {notes.map((note) => (
                  <p key={note} className="rounded-md bg-surface px-3 py-2 text-sm leading-6 text-neutral-700">
                    {note}
                  </p>
                ))}
              </div>
            ) : null}
          </aside>
        </section>
      </div>
    </AppShell>
  );
}
