"use client";

import { useMemo, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";

const LIMIT = 1200;

export default function ToolsPage() {
  const [tab, setTab] = useState<"translate" | "quiz">("translate");
  const [text, setText] = useState("");
  const clipped = text.slice(0, LIMIT);
  const quizItems = useMemo(() => buildQuiz(clipped), [clipped]);

  return (
    <AppShell>
      <div className="mb-6">
        <p className="text-sm font-semibold uppercase text-accent">Experimental</p>
        <h1 className="mt-2 text-2xl font-semibold">Learning tools</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-600">
          Small, fast helpers for offline workflows. These are UI-first prototypes; model-backed translation and quiz generation can plug into the same panels.
        </p>
      </div>
      <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
        <div className="flex gap-2 rounded-lg bg-surface p-1">
          {(["translate", "quiz"] as const).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setTab(item)}
              className={`flex-1 rounded-md px-3 py-2 text-sm font-semibold capitalize ${
                tab === item ? "bg-panel text-accent shadow-sm" : "text-neutral-600 hover:bg-white"
              }`}
            >
              {item === "translate" ? "Translate" : "Quiz maker"}
            </button>
          ))}
        </div>
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={10}
          maxLength={LIMIT}
          placeholder={tab === "translate" ? "Paste a short passage for focused translation." : "Paste text to draft quick review questions."}
          className="mt-5 w-full resize-y rounded-md border border-line px-3 py-2 text-sm leading-6"
        />
        <div className="mt-2 text-right text-xs font-medium text-neutral-500">{clipped.length}/{LIMIT}</div>

        {tab === "translate" ? (
          <section className="mt-5 rounded-lg bg-surface p-4 text-sm leading-6 text-neutral-800">
            <p className="font-semibold">Translation draft</p>
            <p className="mt-2 text-neutral-600">
              Model-backed offline translation will run here with a strict character limit. For now, this panel defines the UX: short passage in, focused translation out, then save useful expressions to dictionary.
            </p>
          </section>
        ) : (
          <section className="mt-5 space-y-3">
            {quizItems.length ? (
              quizItems.map((item, index) => (
                <div key={item} className="rounded-lg border border-line bg-surface p-4 text-sm">
                  <p className="font-semibold">Q{index + 1}. What does this expression mean in context?</p>
                  <p className="mt-2 text-neutral-700">{item}</p>
                </div>
              ))
            ) : (
              <div className="rounded-lg bg-surface p-4 text-sm text-neutral-600">Paste text to draft quiz prompts.</div>
            )}
          </section>
        )}
      </div>
    </AppShell>
  );
}

function buildQuiz(text: string) {
  return Array.from(
    new Set(
      text
        .split(/[.!?\n]/)
        .map((line) => line.trim())
        .filter((line) => line.split(/\s+/).length >= 6)
        .slice(0, 5)
    )
  );
}
