export function LoadingState({ label = "Loading" }: { label?: string }) {
  return <div className="rounded-lg border border-line bg-panel p-5 text-sm text-neutral-600">{label}...</div>;
}
