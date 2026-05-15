"use client";

import { CheckCircle2, Cloud, Cpu, FlaskConical } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ModelPreset, ModelStatus } from "@/lib/types";

const runtimeIcon = {
  mock: FlaskConical,
  mlx: Cpu,
  ollama: Cloud
};

export function ModelStatusCard({ status }: { status: ModelStatus | null }) {
  const [current, setCurrent] = useState(status);
  const [presets, setPresets] = useState<ModelPreset[]>([]);
  const [busyPreset, setBusyPreset] = useState<string | null>(null);

  useEffect(() => {
    api.listModelPresets().then(setPresets).catch(() => setPresets([]));
  }, []);

  async function selectPreset(preset: ModelPreset) {
    setBusyPreset(preset.id);
    try {
      const updated = await api.updateModelConfig({ preset_id: preset.id });
      setCurrent(updated);
    } finally {
      setBusyPreset(null);
    }
  }

  return (
    <div className="rounded-lg border border-line bg-panel p-4 shadow-material">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-neutral-500">Model preset</p>
          <h2 className="mt-1 text-base font-semibold text-ink">{current?.preset_label ?? "Backend offline"}</h2>
        </div>
        {current ? <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold uppercase text-accent">{current.provider}</span> : null}
      </div>

      {current ? (
        <div className="mt-4 space-y-2">
          {presets.map((preset) => {
            const Icon = runtimeIcon[preset.runtime];
            const selected = current.preset_id === preset.id;
            const disabled = preset.availability === "missing";
            return (
              <button
                key={preset.id}
                onClick={() => selectPreset(preset)}
                disabled={disabled || busyPreset !== null}
                className={`w-full rounded-lg border p-3 text-left transition ${selected ? "border-accent bg-blue-50" : "border-line bg-white hover:bg-surface"} disabled:cursor-not-allowed disabled:opacity-55`}
              >
                <div className="flex items-start gap-3">
                  <Icon size={18} className={selected ? "text-accent" : "text-neutral-500"} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-ink">{preset.label}</p>
                      {selected ? <CheckCircle2 size={16} className="text-accent" /> : null}
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs text-neutral-600">{preset.description}</p>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs">
                      <span className="rounded-full bg-surface px-2 py-1">{preset.size}</span>
                      <span className="rounded-full bg-surface px-2 py-1">{preset.speed}</span>
                      <span className={`rounded-full px-2 py-1 ${preset.availability === "ready" ? "bg-green-50 text-green-700" : preset.availability === "external" ? "bg-amber-50 text-amber" : "bg-red-50 text-red-700"}`}>
                        {preset.availability}
                      </span>
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <p className="mt-3 text-sm text-neutral-600">Start the backend to select a model.</p>
      )}
    </div>
  );
}
