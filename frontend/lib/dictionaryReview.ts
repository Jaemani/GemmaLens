import type { DictionaryItem } from "./types";

export type ReviewState = "new" | "review-soon" | "familiar";

export function reviewState(item: DictionaryItem): ReviewState {
  if (item.view_count <= 0) return "new";
  if (item.view_count < Math.max(2, item.encounter_count)) return "review-soon";
  return "familiar";
}

export function reviewLabel(state: ReviewState) {
  if (state === "new") return "New";
  if (state === "review-soon") return "Learning";
  return "Familiar";
}

export function reviewTone(state: ReviewState) {
  if (state === "new") return "bg-blue-50 text-accent";
  if (state === "review-soon") return "bg-amber-50 text-amber-800";
  return "bg-emerald-50 text-emerald-700";
}

export function reviewCounts(items: DictionaryItem[]) {
  return items.reduce(
    (counts, item) => {
      counts[reviewState(item)] += 1;
      return counts;
    },
    { new: 0, "review-soon": 0, familiar: 0 }
  );
}
