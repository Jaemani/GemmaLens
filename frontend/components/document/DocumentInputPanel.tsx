"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { DocumentUploadCard } from "./DocumentUploadCard";

const SAMPLE_TEXT = "Although previous studies have suggested a correlation between sleep deprivation and reduced cognitive performance, the extent to which these findings generalize across real-world learning environments remains unclear. To address this gap, we analyze longitudinal study logs collected from undergraduate students over a six-week period.";

export function DocumentInputPanel() {
  const router = useRouter();
  const [title, setTitle] = useState("Sleep and learning excerpt");
  const [content, setContent] = useState(SAMPLE_TEXT);
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    try {
      const document = await api.createDocument({ title, content, source_type: "text" });
      await api.analyzeDocument(document.id);
      router.push(`/analysis/${document.id}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="grid gap-5 lg:grid-cols-[1fr_320px]">
      <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
        <label className="text-sm font-semibold" htmlFor="title">Title</label>
        <input id="title" value={title} onChange={(event) => setTitle(event.target.value)} className="mt-2 w-full rounded-md border border-line px-3 py-2" />
        <label className="mt-5 block text-sm font-semibold" htmlFor="content">Document text</label>
        <textarea id="content" value={content} onChange={(event) => setContent(event.target.value)} rows={14} className="mt-2 w-full resize-y rounded-md border border-line px-3 py-2 leading-6" />
        <div className="mt-4 flex justify-end">
          <button disabled={busy || !content.trim()} onClick={submit} className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            {busy ? "Analyzing..." : "Analyze document"}
          </button>
        </div>
      </div>
      <DocumentUploadCard onText={(fileName, text) => { setTitle(fileName); setContent(text); }} />
    </section>
  );
}
