import type { DictionaryItem } from "@/lib/types";
import { reviewLabel, reviewState, reviewTone } from "@/lib/dictionaryReview";

export function SavedTermCard({ item }: { item: DictionaryItem }) {
  const state = reviewState(item);
  return (
    <article className="rounded-lg border border-line bg-panel p-4 shadow-material">
      <div className="flex items-start justify-between gap-3">
        <div>
          <TypeChip type={item.item_type} />
          <h3 className="mt-1 font-semibold">{item.text}</h3>
        </div>
        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${reviewTone(state)}`}>{reviewLabel(state)}</span>
      </div>
      {item.meaning ? <p className="mt-3 text-sm text-neutral-700">{item.meaning}</p> : null}
      <p className="mt-3 text-xs text-neutral-500">
        Saved {item.encounter_count} time{item.encounter_count === 1 ? "" : "s"} · reviewed {item.view_count} time{item.view_count === 1 ? "" : "s"}
      </p>
    </article>
  );
}

function TypeChip({ type }: { type: DictionaryItem["item_type"] }) {
  const label = type === "phrase" ? "Expression" : type.charAt(0).toUpperCase() + type.slice(1);
  const tone = {
    concept: "bg-blue-50 text-accent",
    term: "bg-emerald-50 text-emerald-700",
    phrase: "bg-amber-50 text-amber-800",
    sentence: "bg-violet-50 text-violet-700"
  }[type];
  return <span className={`inline-flex rounded-full px-2 py-1 text-[11px] font-semibold ${tone}`}>{label}</span>;
}
