"use client";

import { Upload } from "lucide-react";

export function DocumentUploadCard({ onText }: { onText: (title: string, text: string) => void }) {
  async function handleFile(file: File | null) {
    if (!file) return;
    const text = await file.text();
    onText(file.name, text);
  }

  return (
    <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-line bg-panel p-6 text-center hover:bg-surface">
      <Upload size={24} className="text-accent" />
      <span className="mt-3 text-sm font-semibold">Upload text or markdown</span>
      <span className="mt-1 text-xs text-neutral-500">PDF is supported by backend endpoint; this panel reads local text files.</span>
      <input className="sr-only" type="file" accept=".txt,.md,.markdown" onChange={(event) => handleFile(event.target.files?.[0] ?? null)} />
    </label>
  );
}
