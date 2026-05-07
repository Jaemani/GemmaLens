import type { DocumentListItem } from "@/lib/types";
import Link from "next/link";

export function DocumentPreview({ documents }: { documents: DocumentListItem[] }) {
  return (
    <section className="rounded-lg border border-line bg-panel p-5 shadow-material">
      <h2 className="text-lg font-semibold">Recent documents</h2>
      <div className="mt-4 space-y-3">
        {documents.map((document) => (
          <Link key={document.id} href={`/analysis/${document.id}`} className="block rounded-md border border-line p-3 hover:bg-surface">
            <div className="flex items-center justify-between gap-3">
              <p className="font-medium">{document.title}</p>
              <span className="text-xs uppercase text-neutral-500">{document.source_type}</span>
            </div>
            <p className="mt-2 line-clamp-2 text-sm text-neutral-600">{document.preview}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
