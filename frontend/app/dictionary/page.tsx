"use client";

import { useEffect, useState } from "react";
import { DictionaryTable } from "@/components/dictionary/DictionaryTable";
import { EmptyState } from "@/components/common/EmptyState";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import { reviewCounts } from "@/lib/dictionaryReview";
import type { DictionaryItem } from "@/lib/types";

export default function DictionaryPage() {
  const [items, setItems] = useState<DictionaryItem[]>([]);
  const [filter, setFilter] = useState<DictionaryFilter>("all");

  async function load() {
    try {
      setItems(await api.listDictionary());
    } catch {
      setItems([]);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filteredItems = filter === "all" ? items : items.filter((item) => item.item_type === filter);
  const counts = countByType(items);
  const review = reviewCounts(items);

  return (
    <AppShell>
      <div className="mb-5 flex items-baseline justify-between gap-4">
        <h1 className="text-xl font-semibold">Library</h1>
        <div className="flex items-center gap-4 text-xs text-neutral-500">
          <span>New: <strong className="text-ink">{review.new}</strong></span>
          <span>Learning: <strong className="text-ink">{review["review-soon"]}</strong></span>
          <span>Familiar: <strong className="text-ink">{review.familiar}</strong></span>
        </div>
      </div>
      {items.length === 0 ? (
        <EmptyState title="No saved items" detail="Save concepts, terms, expressions, or sentence patterns from an analysis result to build your review queue." />
      ) : (
        <div className="space-y-4">
          {/* Filter tabs */}
          <div className="flex flex-wrap gap-1.5">
            {([
              { id: "all", label: "All", count: items.length },
              { id: "concept", label: "Key ideas", count: counts.concept },
              { id: "term", label: "Terms", count: counts.term },
              { id: "phrase", label: "Phrases", count: counts.phrase },
              { id: "sentence", label: "Patterns", count: counts.sentence },
            ] as { id: DictionaryFilter; label: string; count: number }[]).map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setFilter(tab.id)}
                className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-xs font-semibold transition ${
                  filter === tab.id
                    ? "border-accent bg-accent text-white"
                    : "border-line bg-panel text-neutral-600 hover:bg-surface hover:text-ink"
                }`}
              >
                {tab.label}
                <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${
                  filter === tab.id ? "bg-white/20 text-white" : "bg-neutral-100 text-neutral-500"
                }`}>
                  {tab.count}
                </span>
              </button>
            ))}
          </div>
          <DictionaryTable items={filteredItems} onDeleted={load} />
        </div>
      )}
    </AppShell>
  );
}
type DictionaryFilter = "all" | DictionaryItem["item_type"];

function countByType(items: DictionaryItem[]) {
  return items.reduce(
    (counts, item) => {
      counts[item.item_type] += 1;
      return counts;
    },
    { concept: 0, term: 0, phrase: 0, sentence: 0 }
  );
}
