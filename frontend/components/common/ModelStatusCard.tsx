"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { ModelStatus } from "@/lib/types";

const providers = ["mock", "mlx", "ollama"] as const;

export function ModelStatusCard({ status }: { status: ModelStatus | null }) {
  const [current, setCurrent] = useState(status);
  const [provider, setProvider] = useState<ModelStatus["provider"]>(status?.provider ?? "mock");
  const [mlxModelPath, setMlxModelPath] = useState(status?.mlx_model_path ?? "~/Models/mlx/gemma-4-e4b-it-OptiQ-4bit");
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState(status?.ollama_base_url ?? "http://localhost:11434");
  const [ollamaModel, setOllamaModel] = useState(status?.ollama_model ?? "gemma3:4b");
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    try {
      const updated = await api.updateModelConfig({
        provider,
        mlx_model_path: mlxModelPath,
        ollama_base_url: ollamaBaseUrl,
        ollama_model: ollamaModel
      });
      setCurrent(updated);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
      <p className="text-sm text-neutral-500">Model runtime</p>
      <h2 className="mt-1 text-lg font-semibold uppercase">{current?.provider ?? "offline"}</h2>
      {current ? (
        <div className="mt-3 space-y-2 text-sm text-neutral-700">
          <p>Mock fallback: {current.mock_fallback ? "enabled" : "disabled"}</p>
          <p>MLX model: {current.mlx_model_available ? "available" : "not found"}</p>
          <p className="break-all text-xs text-neutral-500">{current.mlx_model_path}</p>
          <div className="space-y-3 pt-3">
            <div className="flex rounded-md border border-line p-1">
              {providers.map((item) => (
                <button
                  key={item}
                  onClick={() => setProvider(item)}
                  className={`flex-1 rounded px-2 py-1 text-xs font-semibold uppercase ${provider === item ? "bg-accent text-white" : "hover:bg-surface"}`}
                >
                  {item}
                </button>
              ))}
            </div>
            <label className="block text-xs font-semibold text-neutral-500" htmlFor="mlx-path">MLX path</label>
            <input id="mlx-path" value={mlxModelPath} onChange={(event) => setMlxModelPath(event.target.value)} className="w-full rounded-md border border-line px-3 py-2 text-xs" />
            <label className="block text-xs font-semibold text-neutral-500" htmlFor="ollama-url">Ollama URL</label>
            <input id="ollama-url" value={ollamaBaseUrl} onChange={(event) => setOllamaBaseUrl(event.target.value)} className="w-full rounded-md border border-line px-3 py-2 text-xs" />
            <label className="block text-xs font-semibold text-neutral-500" htmlFor="ollama-model">Ollama model</label>
            <input id="ollama-model" value={ollamaModel} onChange={(event) => setOllamaModel(event.target.value)} className="w-full rounded-md border border-line px-3 py-2 text-xs" />
            <button onClick={save} disabled={busy} className="w-full rounded-md bg-accent px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">
              {busy ? "Saving..." : "Save runtime"}
            </button>
          </div>
        </div>
      ) : (
        <p className="mt-3 text-sm text-neutral-600">Backend unavailable.</p>
      )}
    </div>
  );
}
