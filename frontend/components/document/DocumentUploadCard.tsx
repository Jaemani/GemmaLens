"use client";

import { Upload } from "lucide-react";

export function DocumentUploadCard({ disabled, onFile }: { disabled?: boolean; onFile: (file: File) => void }) {
  return (
    <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-line bg-panel p-6 text-center hover:bg-surface has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-60">
      <Upload size={24} className="text-accent" />
      <span className="mt-3 text-sm font-semibold">Upload document</span>
      <span className="mt-1 text-xs text-neutral-500">Text, markdown, and basic PDF extraction use the backend parser.</span>
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
