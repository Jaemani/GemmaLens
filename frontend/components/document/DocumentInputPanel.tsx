"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { AnalysisProgress } from "@/components/analysis/AnalysisProgress";
import { DocumentUploadCard } from "./DocumentUploadCard";

const SAMPLE_TEXT = "Although previous studies have suggested a correlation between sleep deprivation and reduced cognitive performance, the extent to which these findings generalize across real-world learning environments remains unclear. To address this gap, we analyze longitudinal study logs collected from undergraduate students over a six-week period.";

export function DocumentInputPanel() {
  const router = useRouter();
  const [title, setTitle] = useState("Sleep and learning excerpt");
  const [content, setContent] = useState(SAMPLE_TEXT);
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [progressTitle, setProgressTitle] = useState("Preparing document");

  async function runWithProgress(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setStatus(null);
    setProgressTitle("Preparing document");
    setElapsed(0);
    setStep(0);
    const timer = window.setInterval(() => {
      setElapsed((value) => value + 1);
    }, 1000);
    try {
      await action();
      setStep(4);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis or upload failed.");
    } finally {
      window.clearInterval(timer);
      setBusy(false);
    }
  }

  async function submit() {
    await runWithProgress(async () => {
      setProgressTitle("Preparing document");
      setStep(0);
      setStatus("Creating document record...");
      const document = await api.createDocument({ title, content, source_type: "text" });
      setStep(2);
      setProgressTitle("Analyzing document");
      setStatus("Running model analysis...");
      await api.analyzeDocument(document.id);
      setStep(4);
      setProgressTitle("Opening result");
      setStatus("Opening result...");
      router.push(`/analysis/${document.id}`);
    });
  }

  async function uploadAndAnalyze(file: File) {
    await runWithProgress(async () => {
      setProgressTitle("Uploading document");
      setStep(1);
      setStatus(`Uploading ${file.name} and extracting text...`);
      const document = await api.uploadDocument(file);
      setStep(2);
      setProgressTitle("Analyzing document");
      setStatus(`Text extracted from ${file.name}. Running model analysis...`);
      await api.analyzeDocument(document.id);
      setStep(4);
      setProgressTitle("Opening result");
      setStatus("Opening result...");
      router.push(`/analysis/${document.id}`);
    });
  }

  return (
    <section className="grid gap-5 lg:grid-cols-[1fr_320px]">
      <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
        <label className="text-sm font-semibold" htmlFor="title">Title</label>
        <input id="title" value={title} onChange={(event) => setTitle(event.target.value)} className="mt-2 w-full rounded-md border border-line px-3 py-2" />
        <label className="mt-5 block text-sm font-semibold" htmlFor="content">Document text</label>
        <textarea id="content" value={content} onChange={(event) => setContent(event.target.value)} rows={14} className="mt-2 w-full resize-y rounded-md border border-line px-3 py-2 leading-6" />
        <div className="mt-4 flex justify-end">
          <div className="flex flex-wrap justify-end gap-3">
            <Link href="/analysis/demo" className="rounded-md border border-line px-4 py-2 text-sm font-semibold text-ink hover:bg-surface">
              Open demo result
            </Link>
            <button disabled={busy || !content.trim()} onClick={submit} className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
              {busy ? "Analyzing..." : "Analyze document"}
            </button>
          </div>
        </div>
        {error ? (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <p className="font-semibold">Request failed</p>
            <p className="mt-1">{error}</p>
          </div>
        ) : null}
      </div>
      <div className="space-y-5">
        <DocumentUploadCard disabled={busy} onFile={uploadAndAnalyze} />
        {!busy && status ? <p className="rounded-lg border border-line bg-panel px-4 py-3 text-sm font-medium text-neutral-700 shadow-material">{status}</p> : null}
        {busy ? <AnalysisProgress step={step} elapsed={elapsed} title={progressTitle} currentLabel={status} /> : null}
      </div>
    </section>
  );
}
