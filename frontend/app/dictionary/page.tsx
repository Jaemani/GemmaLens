"use client";

import { GitBranch, Layers, Quote, ScanText, Sparkles } from "lucide-react";
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
          <section className="rounded-lg border border-line bg-panel shadow-material">
            <div className="border-b border-line px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Library layers</p>
              <p className="mt-1 text-sm leading-6 text-neutral-600">
                Concepts explain the paper. Terms, expressions, and sentence patterns support English reading.
              </p>
            </div>
            <div className="divide-y divide-line">
              <FilterRow
                icon={<Sparkles size={16} />}
                title="All saved items"
                detail="Everything saved from papers, docs, and videos."
                active={filter === "all"}
                count={items.length}
                onClick={() => setFilter("all")}
              />
              <FilterRow
                icon={<GitBranch size={16} />}
                title="Concept layer"
                detail="Ideas and domain knowledge to connect across sources."
                active={filter === "concept"}
                count={counts.concept}
                onClick={() => setFilter("concept")}
              />
              <div className="grid gap-0 md:grid-cols-3 md:divide-x md:divide-line">
                <FilterRow
                  icon={<Layers size={16} />}
                  title="Terms"
                  detail="Technical vocabulary and native-language glosses."
                  active={filter === "term"}
                  count={counts.term}
                  compact
                  onClick={() => setFilter("term")}
                />
                <FilterRow
                  icon={<Quote size={16} />}
                  title="Expressions"
                  detail="Academic phrases and reusable discourse moves."
                  active={filter === "phrase"}
                  count={counts.phrase}
                  compact
                  onClick={() => setFilter("phrase")}
                />
                <FilterRow
                  icon={<ScanText size={16} />}
                  title="Sentences"
                  detail="Hard sentence patterns worth reviewing."
                  active={filter === "sentence"}
                  count={counts.sentence}
                  compact
                  onClick={() => setFilter("sentence")}
                />
              </div>
            </div>
          </section>
          <section className="rounded-lg border border-line bg-surface px-4 py-3">
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
              <span className="font-semibold text-ink">Review queue</span>
              <span className="text-neutral-600">New: <strong className="text-ink">{review.new}</strong></span>
              <span className="text-neutral-600">Review next: <strong className="text-ink">{review["review-soon"]}</strong></span>
              <span className="text-neutral-600">Stable: <strong className="text-ink">{review.familiar}</strong></span>
            </div>
          </section>
          <section className="rounded-lg border-l-4 border-accent bg-panel p-4 shadow-material">
            <div className="flex items-start gap-3">
              <div className="rounded-md bg-surface p-2 text-accent">
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

function FilterRow({
  icon,
  title,
  detail,
  count,
  active,
  compact = false,
  onClick
}: {
  icon: ReactNode;
  title: string;
  detail: string;
  count: number;
  active: boolean;
  compact?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center justify-between gap-4 px-4 py-3 text-left transition ${
        active ? "bg-blue-50 text-accent" : "text-ink hover:bg-surface"
      } ${compact ? "md:min-h-28" : ""}`}
    >
      <div className="flex min-w-0 items-start gap-3">
        <div className={`mt-0.5 rounded-md p-2 ${active ? "bg-white text-accent" : "bg-surface text-neutral-600"}`}>{icon}</div>
        <div className="min-w-0">
          <p className="text-sm font-semibold">{title}</p>
          <p className="mt-1 text-xs leading-5 text-neutral-600">{detail}</p>
        </div>
      </div>
      <span className={`shrink-0 text-xl font-semibold ${active ? "text-accent" : "text-ink"}`}>{count}</span>
    </button>
  );
}
