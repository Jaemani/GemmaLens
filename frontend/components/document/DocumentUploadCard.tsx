"use client";

import { Upload } from "lucide-react";

export function DocumentUploadCard({ disabled, onFile }: { disabled?: boolean; onFile: (file: File) => void }) {
  return (
    <label
      className={`flex min-h-56 w-full flex-col items-center justify-center rounded-lg border border-dashed border-line bg-panel p-8 text-center transition ${
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer hover:bg-surface"
      }`}
    >
      <div className="rounded-full bg-blue-50 p-3 text-accent">
        <Upload size={28} />
      </div>
      <span className="mt-4 text-base font-semibold">{disabled ? "Processing document..." : "Upload document"}</span>
      <span className="mt-2 max-w-sm text-sm leading-6 text-neutral-600">
        PDF, text, and markdown. GemmaLens extracts the text first, then runs structured learning analysis.
      </span>
      <span className="mt-4 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white">
        Choose file
      </span>
      <input
        className="sr-only"
        type="file"
        accept=".txt,.md,.markdown,.pdf,text/plain,text/markdown,application/pdf"
        disabled={disabled}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFile(file);
          event.target.value = "";
        }}
      />
    </label>
  );
}
