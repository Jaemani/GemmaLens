"use client";

import Link from "next/link";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import type { DocumentListItem } from "@/lib/types";

export function DocumentPreview({ documents }: { documents: DocumentListItem[] }) {
  const [items, setItems] = useState(documents);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function remove(document: DocumentListItem) {
    setDeletingId(document.id);
    setError(null);
    try {
      await api.deleteDocument(document.id);
      window.localStorage.removeItem(`paperlens.quiz.${document.id}`);
      setItems((current) => current.filter((item) => item.id !== document.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete document.");
    } finally {
      setDeletingId(null);
    }
  }

  if (!items.length) return null;

  return (
    <section className="rounded-lg border border-line bg-panel p-5 shadow-material">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Recent documents</h2>
        <span className="text-xs font-semibold uppercase text-neutral-500">{items.length} items</span>
      </div>
      {error ? <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">{error}</p> : null}
      <div className="mt-4 space-y-3">
        {items.map((document) => (
          <div key={document.id} className="grid gap-2 rounded-md border border-line p-3 hover:bg-surface sm:grid-cols-[minmax(0,1fr)_auto]">
            <Link href={`/analysis/${document.id}`} className="min-w-0">
              <div className="flex items-center justify-between gap-3">
                <p className="truncate font-medium">{document.title}</p>
                <span className="shrink-0 text-xs uppercase text-neutral-500">{document.source_type}</span>
              </div>
              <p className="mt-2 line-clamp-2 text-sm text-neutral-600">{document.preview}</p>
            </Link>
            <button
              type="button"
              onClick={() => remove(document)}
              disabled={deletingId === document.id}
              className="inline-flex items-center justify-center gap-2 rounded-md border border-line px-3 py-2 text-xs font-semibold text-neutral-600 hover:bg-white disabled:opacity-50"
              aria-label={`Delete ${document.title}`}
            >
              <Trash2 size={14} />
              {deletingId === document.id ? "Deleting" : "Delete"}
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
