"use client";

import { Upload } from "lucide-react";
import { useRef } from "react";

export function DocumentUploadCard({ disabled, onFile }: { disabled?: boolean; onFile: (file: File) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className={`rounded-lg border border-line bg-panel p-5 ${disabled ? "opacity-60" : ""}`}>
      <div className="flex items-start gap-4">
        <div className="rounded-md bg-blue-50 p-3 text-accent">
          <Upload size={24} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-semibold">{disabled ? "Processing document..." : "Upload document"}</p>
          <p className="mt-1 text-sm leading-6 text-neutral-600">
            Select a PDF, DOCX, text, or markdown file. GemmaLens extracts text first, then runs structured learning analysis.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              disabled={disabled}
              onClick={() => inputRef.current?.click()}
              className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-neutral-300 disabled:text-neutral-600"
            >
              <Upload size={16} />
              Choose file
            </button>
            <span className="text-xs font-medium text-neutral-500">PDF, DOCX, TXT, MD</span>
          </div>
        </div>
      </div>
      <input
        ref={inputRef}
        className="sr-only"
        type="file"
        accept=".txt,.md,.markdown,.pdf,.docx,text/plain,text/markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        disabled={disabled}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFile(file);
          event.target.value = "";
        }}
      />
    </div>
  );
}
