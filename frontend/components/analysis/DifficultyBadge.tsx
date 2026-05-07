export function DifficultyBadge({ level }: { level: string }) {
  return <span className="rounded-full bg-amber/10 px-3 py-1 text-xs font-semibold uppercase text-amber">{level}</span>;
}
