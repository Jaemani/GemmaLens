import type { ModelStatus } from "@/lib/types";

export function ModelStatusCard({ status }: { status: ModelStatus | null }) {
  const provider = status?.provider ?? "offline";
  const available = status?.mlx_model_available;

  return (
    <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
      <p className="text-sm text-neutral-500">Model runtime</p>
      <h2 className="mt-1 text-lg font-semibold uppercase">{provider}</h2>
      {status ? (
        <div className="mt-3 space-y-2 text-sm text-neutral-700">
          <p>Mock fallback: {status.mock_fallback ? "enabled" : "disabled"}</p>
          <p>MLX model: {available ? "available" : "not found"}</p>
          <p className="break-all text-xs text-neutral-500">{status.mlx_model_path}</p>
        </div>
      ) : (
        <p className="mt-3 text-sm text-neutral-600">Backend unavailable.</p>
      )}
    </div>
  );
}
