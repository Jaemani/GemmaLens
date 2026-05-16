"use client";

import { BookOpenCheck, Filter, Layers, Quote, RotateCcw, ScanText, Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { DictionaryTable } from "@/components/dictionary/DictionaryTable";
import { SavedTermCard } from "@/components/dictionary/SavedTermCard";
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
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Dictionary</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">
          Saved concepts, terms, expressions, and sentence patterns from analyzed documents. Use this as a review queue, not as a raw word dump.
        </p>
      </div>
      {items.length === 0 ? (
        <EmptyState title="No saved items" detail="Save concepts, terms, expressions, or sentence patterns from an analysis result to build your review queue." />
      ) : (
        <div className="space-y-6">
          <section className="grid gap-3 md:grid-cols-4">
            <SummaryCard icon={<Layers size={18} />} label="Concepts" count={counts.concept} />
            <SummaryCard icon={<ScanText size={18} />} label="Terms" count={counts.term} />
            <SummaryCard icon={<Quote size={18} />} label="Expressions" count={counts.phrase} />
            <SummaryCard icon={<BookOpenCheck size={18} />} label="Sentences" count={counts.sentence} />
          </section>
          <section className="grid gap-3 md:grid-cols-3">
            <SummaryCard icon={<Sparkles size={18} />} label="New" count={review.new} tone="blue" />
            <SummaryCard icon={<RotateCcw size={18} />} label="Review soon" count={review["review-soon"]} tone="amber" />
            <SummaryCard icon={<BookOpenCheck size={18} />} label="Familiar" count={review.familiar} tone="emerald" />
          </section>
          <section className="rounded-lg border border-line bg-panel p-4 shadow-material">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-ink">
                <Filter size={16} className="text-accent" />
                Review focus
              </div>
              <div className="flex flex-wrap gap-2">
                {(["all", "concept", "term", "phrase", "sentence"] as const).map((value) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setFilter(value)}
                    className={`rounded-md border px-3 py-1.5 text-xs font-semibold ${
                      filter === value ? "border-accent bg-blue-50 text-accent" : "border-line text-neutral-600 hover:bg-surface"
                    }`}
                  >
                    {filterLabel(value)}
                  </button>
                ))}
              </div>
            </div>
          </section>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {filteredItems.slice(0, 6).map((item) => <SavedTermCard key={item.id} item={item} />)}
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

function filterLabel(value: DictionaryFilter) {
  if (value === "all") return "All";
  if (value === "phrase") return "Expressions";
  return `${value.charAt(0).toUpperCase()}${value.slice(1)}s`;
}

function SummaryCard({ icon, label, count, tone = "blue" }: { icon: ReactNode; label: string; count: number; tone?: "blue" | "amber" | "emerald" }) {
  const toneClass = {
    blue: "bg-blue-50 text-accent",
    amber: "bg-amber-50 text-amber-800",
    emerald: "bg-emerald-50 text-emerald-700"
  }[tone];
  return (
    <div className="rounded-lg border border-line bg-panel p-4 shadow-material">
      <div className="flex items-center justify-between gap-3">
        <div className={`rounded-md p-2 ${toneClass}`}>{icon}</div>
        <span className="text-2xl font-semibold text-ink">{count}</span>
      </div>
      <p className="mt-3 text-sm font-semibold text-neutral-700">{label}</p>
    </div>
  );
}
