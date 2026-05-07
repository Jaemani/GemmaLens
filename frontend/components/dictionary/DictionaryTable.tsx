"use client";

import { Eye, Trash2 } from "lucide-react";
import type { DictionaryItem } from "@/lib/types";
import { api } from "@/lib/api";

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
      <table className="w-full text-left text-sm">
        <thead className="bg-surface text-xs uppercase text-neutral-500">
          <tr>
            <th className="px-4 py-3">Item</th>
            <th className="px-4 py-3">Meaning</th>
            <th className="px-4 py-3">Seen</th>
            <th className="px-4 py-3">Viewed</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className="border-t border-line">
              <td className="px-4 py-3">
                <p className="font-medium">{item.text}</p>
                <p className="text-xs uppercase text-neutral-500">{item.item_type}</p>
              </td>
              <td className="px-4 py-3 text-neutral-700">{item.meaning}</td>
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
