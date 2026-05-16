"use client";

import { BookOpenCheck, GitBranch, Layers, Quote, RotateCcw, ScanText, Sparkles } from "lucide-react";
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
  const sourceCount = new Set(items.map((item) => item.document_id).filter(Boolean)).size;

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Learning Library</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">
          Saved concepts, terms, expressions, and sentence patterns from papers, docs, and videos. This is a study library and review queue, not a raw word list.
        </p>
      </div>
      {items.length === 0 ? (
        <EmptyState title="No saved items" detail="Save concepts, terms, expressions, or sentence patterns from an analysis result to build your review queue." />
      ) : (
        <div className="space-y-6">
          <section className="grid gap-3 md:grid-cols-5">
            {(["all", "concept", "term", "phrase", "sentence"] as const).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setFilter(value)}
                className={`rounded-lg border p-4 text-left shadow-material ${
                  filter === value ? "border-accent bg-blue-50 text-accent" : "border-line bg-panel text-ink hover:bg-surface"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-semibold">{filterLabel(value)}</span>
                  <span className="text-2xl font-semibold">{value === "all" ? items.length : counts[value]}</span>
                </div>
              </button>
            ))}
          </section>
          <section className="grid gap-3 md:grid-cols-3">
            <SummaryCard icon={<Sparkles size={18} />} label="New" count={review.new} tone="blue" />
            <SummaryCard icon={<RotateCcw size={18} />} label="Review next" count={review["review-soon"]} tone="amber" />
            <SummaryCard icon={<BookOpenCheck size={18} />} label="Stable" count={review.familiar} tone="emerald" />
          </section>
          <section className="rounded-lg border border-line bg-panel p-4 shadow-material">
            <div className="flex items-start gap-3">
              <div className="rounded-md bg-blue-50 p-2 text-accent">
                <GitBranch size={18} />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-ink">Connections</h2>
                <p className="mt-1 text-sm leading-6 text-neutral-600">
                  {sourceCount || 1} source{sourceCount === 1 ? "" : "s"} · {counts.concept} concepts · {counts.term} terms · {counts.phrase} expressions.
                  Use the type tabs above to inspect each layer. A graph/wiki view can build on these saved items by linking repeated terms across papers, videos, and docs.
                </p>
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
