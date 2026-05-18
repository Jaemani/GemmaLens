"use client";

import { Eye, Trash2 } from "lucide-react";
import type { DictionaryItem } from "@/lib/types";
import { api } from "@/lib/api";
import { reviewLabel, reviewState, reviewTone } from "@/lib/dictionaryReview";

export function DictionaryTable({ items, onDeleted }: { items: DictionaryItem[]; onDeleted: () => void }) {
  async function remove(itemId: string) {
    await api.deleteDictionaryItem(itemId);
    onDeleted();
  }

  async function markViewed(itemId: string) {
    await api.markDictionaryViewed(itemId);
    onDeleted();
  }

  return (
    <section className="overflow-hidden rounded-lg border border-line bg-panel shadow-material">
      <div className="grid gap-3 p-3 md:hidden">
        {items.map((item) => {
          const state = reviewState(item);
          return (
            <article key={item.id} className="rounded-md border border-line bg-surface p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <TypeChip type={item.item_type} />
                  <h3 className="mt-1 break-words text-sm font-semibold text-ink">{item.text}</h3>
                </div>
                <span className={`shrink-0 rounded-full px-2 py-1 text-xs font-semibold ${reviewTone(state)}`}>
                  {reviewLabel(state)}
                </span>
              </div>
              {item.meaning ? <p className="mt-3 text-sm leading-6 text-neutral-700">{item.meaning}</p> : null}
              {item.source_sentence ? <p className="mt-3 rounded-md bg-white p-3 text-xs leading-5 text-neutral-600">{item.source_sentence}</p> : null}
              <div className="mt-3 flex items-center justify-between gap-3">
                <p className="text-xs text-neutral-500">
                  Saved {item.encounter_count} time{item.encounter_count === 1 ? "" : "s"} · reviewed {item.view_count} time{item.view_count === 1 ? "" : "s"}
                </p>
                <div className="flex gap-1">
                  <button aria-label="Mark viewed" onClick={() => markViewed(item.id)} className="rounded-md p-2 hover:bg-white">
                    <Eye size={16} />
                  </button>
                  <button aria-label="Delete item" onClick={() => remove(item.id)} className="rounded-md p-2 hover:bg-white">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </article>
          );
        })}
      </div>
      <table className="hidden w-full text-left text-sm md:table">
        <thead className="bg-surface text-xs uppercase text-neutral-500">
          <tr>
            <th className="px-4 py-3">Item</th>
            <th className="px-4 py-3">Meaning</th>
            <th className="px-4 py-3">Review</th>
            <th className="px-4 py-3">Saved</th>
            <th className="px-4 py-3">Reviewed</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className="border-t border-line">
              <td className="px-4 py-3">
                <p className="font-medium">{item.text}</p>
                <div className="mt-1">
                  <TypeChip type={item.item_type} />
                </div>
              </td>
              <td className="px-4 py-3 text-neutral-700">{item.meaning}</td>
              <td className="px-4 py-3">
                <span className={`rounded-full px-2 py-1 text-xs font-semibold ${reviewTone(reviewState(item))}`}>
                  {reviewLabel(reviewState(item))}
                </span>
              </td>
              <td className="px-4 py-3">{item.encounter_count}</td>
              <td className="px-4 py-3">{item.view_count}</td>
              <td className="px-4 py-3 text-right">
                <button aria-label="Mark viewed" onClick={() => markViewed(item.id)} className="rounded-md p-2 hover:bg-surface">
                  <Eye size={16} />
                </button>
                <button aria-label="Delete item" onClick={() => remove(item.id)} className="rounded-md p-2 hover:bg-surface">
                  <Trash2 size={16} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
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
