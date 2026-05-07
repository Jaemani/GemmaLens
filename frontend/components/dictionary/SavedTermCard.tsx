import type { DictionaryItem } from "@/lib/types";

export function SavedTermCard({ item }: { item: DictionaryItem }) {
  return (
    <article className="rounded-lg border border-line bg-panel p-4 shadow-material">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase text-neutral-500">{item.item_type}</p>
          <h3 className="mt-1 font-semibold">{item.text}</h3>
        </div>
        <span className="rounded-full bg-surface px-2 py-1 text-xs">{item.view_count} views</span>
      </div>
      {item.meaning ? <p className="mt-3 text-sm text-neutral-700">{item.meaning}</p> : null}
    </article>
  );
}
