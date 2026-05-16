import type { DictionaryItem } from "@/lib/types";
import { reviewLabel, reviewState, reviewTone } from "@/lib/dictionaryReview";

export function SavedTermCard({ item }: { item: DictionaryItem }) {
  const state = reviewState(item);
  return (
    <article className="rounded-lg border border-line bg-panel p-4 shadow-material">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase text-neutral-500">{item.item_type}</p>
          <h3 className="mt-1 font-semibold">{item.text}</h3>
        </div>
        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${reviewTone(state)}`}>{reviewLabel(state)}</span>
      </div>
      {item.meaning ? <p className="mt-3 text-sm text-neutral-700">{item.meaning}</p> : null}
      <p className="mt-3 text-xs text-neutral-500">
        Saved hits {item.encounter_count} · opened {item.view_count}
      </p>
    </article>
  );
}
