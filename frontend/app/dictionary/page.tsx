"use client";

import { useEffect, useState } from "react";
import { DictionaryTable } from "@/components/dictionary/DictionaryTable";
import { SavedTermCard } from "@/components/dictionary/SavedTermCard";
import { EmptyState } from "@/components/common/EmptyState";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import type { DictionaryItem } from "@/lib/types";

export default function DictionaryPage() {
  const [items, setItems] = useState<DictionaryItem[]>([]);

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

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Dictionary</h1>
        <p className="mt-2 text-sm text-neutral-600">Saved language items from analyzed documents.</p>
      </div>
      {items.length === 0 ? (
        <EmptyState title="No saved items" detail="Save terms from an analysis result to build your learning dictionary." />
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {items.slice(0, 6).map((item) => <SavedTermCard key={item.id} item={item} />)}
          </div>
          <DictionaryTable items={items} onDeleted={load} />
        </div>
      )}
    </AppShell>
  );
}
