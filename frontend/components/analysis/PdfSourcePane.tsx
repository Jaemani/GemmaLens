"use client";

import { ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import type { DocumentRead } from "@/lib/types";

export function PdfSourcePane({ document }: { document: DocumentRead }) {
  if (document.source_type !== "pdf" || !document.has_original_file) return null;
  const fileUrl = api.documentFileUrl(document.id);
  return (
    <section className="overflow-hidden rounded-lg border border-line bg-panel shadow-material">
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Original PDF</p>
          <h2 className="text-sm font-semibold text-ink">{document.title}</h2>
        </div>
        <a
          href={fileUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-xs font-semibold text-ink hover:bg-surface"
        >
          <ExternalLink size={14} />
          Open
        </a>
      </div>
      <iframe title={document.title} src={fileUrl} className="h-[calc(100vh-170px)] min-h-[640px] w-full bg-white" />
    </section>
  );
}
