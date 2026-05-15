"use client";

import { Clipboard, Languages, RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";
import { LanguageSelect } from "@/components/common/LanguageSelect";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";

const LIMIT = 1200;

export default function ToolsPage() {
  const [sourceLanguage, setSourceLanguage] = useState("English");
  const [targetLanguage, setTargetLanguage] = useState("Korean");
  const [text, setText] = useState("");
  const [result, setResult] = useState("");
  const [notes, setNotes] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [isTranslating, setIsTranslating] = useState(false);
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Translation failed.");
    } finally {
      setIsTranslating(false);
    }
  }

  async function copyResult() {
    if (result) await navigator.clipboard.writeText(result);
  }

  function reset() {
    setText("");
    setResult("");
    setNotes([]);
    setError("");
  }

  return (
    <AppShell>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase text-accent">Focused tool</p>
          <h1 className="mt-2 text-2xl font-semibold">Translate</h1>
        </div>
        <p className="text-xs font-medium text-neutral-500">{LIMIT} character limit</p>
      </div>
      <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
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
            <p className="text-xs font-medium text-neutral-500">{clipped.length}/{LIMIT} chars · {sentenceCount} segments</p>
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
                <Languages size={16} />
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
              Copy
            </button>
          </div>
          <pre className="mt-4 min-h-64 whitespace-pre-wrap rounded-md bg-surface p-4 text-sm leading-6 text-neutral-800">
            {isTranslating ? "Running local model translation..." : result}
          </pre>
          {notes.length ? (
            <div className="mt-4 space-y-2">
              <h3 className="text-xs font-semibold uppercase text-neutral-500">Notes</h3>
              {notes.map((note) => (
                <p key={note} className="rounded-md bg-surface px-3 py-2 text-sm leading-6 text-neutral-700">
                  {note}
                </p>
              ))}
            </div>
          ) : null}
        </aside>
      </section>
    </AppShell>
  );
}
