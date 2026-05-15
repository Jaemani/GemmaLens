"use client";

import { Clipboard, Languages, RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";

const LIMIT = 1200;
const languages = ["English", "Korean", "Spanish", "French", "Japanese"];

export default function ToolsPage() {
  const [sourceLanguage, setSourceLanguage] = useState("English");
  const [targetLanguage, setTargetLanguage] = useState("Korean");
  const [text, setText] = useState("");
  const [result, setResult] = useState("");
  const clipped = text.slice(0, LIMIT);
  const sentenceCount = useMemo(() => clipped.split(/[.!?\n]/).filter((line) => line.trim()).length, [clipped]);

  function translate() {
    if (!clipped.trim()) return;
    setResult(
      `[${sourceLanguage} -> ${targetLanguage}]\n\n${clipped}\n\nModel-backed offline translation will replace this draft. Current interaction keeps the character limit, language pair, copy, and reset flow stable.`
    );
  }

  async function copyResult() {
    if (result) await navigator.clipboard.writeText(result);
  }

  function reset() {
    setText("");
    setResult("");
  }

  return (
    <AppShell>
      <div className="mb-6">
        <p className="text-sm font-semibold uppercase text-accent">Focused tool</p>
        <h1 className="mt-2 text-2xl font-semibold">Translate</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-600">
          Short-passage translation for reading flow. Keep it bounded so edge-device model calls stay fast and predictable.
        </p>
      </div>
      <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
          <div className="grid gap-3 sm:grid-cols-2">
            <Select label="From" value={sourceLanguage} onChange={setSourceLanguage} />
            <Select label="To" value={targetLanguage} onChange={setTargetLanguage} />
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
                disabled={!clipped.trim()}
                className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:bg-neutral-300 disabled:text-neutral-600"
              >
                <Languages size={16} />
                Translate
              </button>
            </div>
          </div>
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
            {result || "Translation output appears here after you run Translate."}
          </pre>
        </aside>
      </section>
    </AppShell>
  );
}

function Select({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="text-sm font-semibold">
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 w-full rounded-md border border-line bg-white px-3 py-2 text-sm">
        {languages.map((language) => <option key={language}>{language}</option>)}
      </select>
    </label>
  );
}
