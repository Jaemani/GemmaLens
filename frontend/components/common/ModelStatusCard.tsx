"use client";

import { CheckCircle2, ChevronDown, ChevronUp, Cloud, Cpu, FlaskConical, Gauge, HardDrive, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ModelPreset, ModelStatus } from "@/lib/types";

const runtimeIcon = {
  mock: FlaskConical,
  mlx: Cpu,
  ollama: Cloud,
  remote: Cloud,
  gguf: HardDrive,
};

// ── Model icons ───────────────────────────────────────────────────────────────

function SparseIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 18 18" fill="none" className={className}>
      <circle cx="9" cy="9" r="2.2" stroke="currentColor" strokeWidth="1.6" />
      <line x1="9" y1="6.8" x2="9" y2="2.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <line x1="11.6" y1="10.2" x2="15" y2="14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <line x1="6.4" y1="10.2" x2="3" y2="14" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeDasharray="1.5 1.5" strokeOpacity="0.4" />
      <line x1="11.2" y1="7.4" x2="15" y2="4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeDasharray="1.5 1.5" strokeOpacity="0.4" />
      <circle cx="9" cy="2" r="1.4" fill="currentColor" />
      <circle cx="15.5" cy="14.5" r="1.4" fill="currentColor" />
      <circle cx="2.5" cy="14.5" r="1.4" stroke="currentColor" strokeWidth="1.2" fill="none" strokeOpacity="0.4" />
      <circle cx="15.5" cy="3.5" r="1.4" stroke="currentColor" strokeWidth="1.2" fill="none" strokeOpacity="0.4" />
    </svg>
  );
}

function DenseIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 18 18" fill="none" className={className}>
      <rect x="1.5" y="1.5"   width="4" height="4" rx="0.8" fill="currentColor" />
      <rect x="7"   y="1.5"   width="4" height="4" rx="0.8" fill="currentColor" />
      <rect x="12.5" y="1.5"  width="4" height="4" rx="0.8" fill="currentColor" />
      <rect x="1.5" y="7"     width="4" height="4" rx="0.8" fill="currentColor" />
      <rect x="7"   y="7"     width="4" height="4" rx="0.8" fill="currentColor" />
      <rect x="12.5" y="7"    width="4" height="4" rx="0.8" fill="currentColor" />
      <rect x="1.5" y="12.5"  width="4" height="4" rx="0.8" fill="currentColor" />
      <rect x="7"   y="12.5"  width="4" height="4" rx="0.8" fill="currentColor" />
      <rect x="12.5" y="12.5" width="4" height="4" rx="0.8" fill="currentColor" />
    </svg>
  );
}

// ── Lineup data ───────────────────────────────────────────────────────────────

const GEMMA4_EDGE = [
  { id: "e2b", name: "E2B", speed: "Fastest",  desc: "Instant gloss and live cues" },
  { id: "e4b", name: "E4B", speed: "Balanced", desc: "Best local lesson quality" },
] as const;

// Optional larger local MLX routes:
// 26B: ~/Models/mlx/gemma-4-26B-A4B-it-OptiQ-4bit
// 31B: ~/Models/mlx/gemma-4-31b-4bit
const GEMMA4_FULL = [
  { id: "26b", name: "26B A4B", speed: "High capability", desc: "Sparse MoE for paper maps", Icon: SparseIcon },
  { id: "31b", name: "31B",     speed: "Max quality",     desc: "Dense model for deep recaps",  Icon: DenseIcon },
] as const;

type GlobalActivity = {
  label: string;
  detail: string;
  href?: string;
  updatedAt: number;
};

function detectActive(label: string): string | null {
  const l = label.toLowerCase();
  if (l.includes("e2b")) return "e2b";
  if (l.includes("e4b")) return "e4b";
  if (l.includes("26b")) return "26b";
  if (l.includes("31b")) return "31b";
  return null;
}

function findPreset(presets: ModelPreset[], lineupId: string): ModelPreset | undefined {
  const matches = presets.filter((p) => {
    const l = p.label.toLowerCase();
    const pid = p.id.toLowerCase();
    if (lineupId === "e2b") return l.includes("e2b") || pid.includes("e2b");
    if (lineupId === "e4b") return l.includes("e4b") || pid.includes("e4b");
    if (lineupId === "26b") return l.includes("26b") || pid === "gemma4-26b-mlx-q4";
    if (lineupId === "31b") return l.includes("31b") || pid === "gemma4-31b-mlx-q4";
    return false;
  });
  return matches.find((p) => p.availability === "ready") ?? matches.find((p) => p.availability !== "missing") ?? matches[0];
}

function modeLabel(provider: string, activeId: string | null): string {
  if (provider === "mock") return "Development mode";
  if (provider === "remote") return "Remote inference";
  if (activeId === "e2b" || activeId === "e4b") return "Edge · On-device · Private";
  if (activeId === "26b") return "Sparse MoE · High cap.";
  if (activeId === "31b") return "Dense · Max quality";
  return "Local inference";
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ModelStatusCard({ status, compact = false }: { status: ModelStatus | null; compact?: boolean }) {
  const [current, setCurrent] = useState(status);
  const [presets, setPresets] = useState<ModelPreset[]>([]);
  const [busyPreset, setBusyPreset] = useState<string | null>(null);
  const [showPresets, setShowPresets] = useState(false);
  const [activeWork, setActiveWork] = useState<GlobalActivity | null>(null);

  useEffect(() => {
    setCurrent(status);
  }, [status]);

  useEffect(() => {
    let cancelled = false;
    async function loadRuntime() {
      try {
        const [nextStatus, nextPresets] = await Promise.all([api.getModelStatus(), api.listModelPresets()]);
        if (cancelled) return;
        setCurrent(nextStatus);
        setPresets(nextPresets);
      } catch {
        if (cancelled) return;
        setPresets([]);
      }
    }
    void loadRuntime();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    function readActiveWork() {
      try {
        const raw = window.localStorage.getItem("gemmalens:active-task");
        if (!raw) {
          setActiveWork(null);
          return;
        }
        const parsed = JSON.parse(raw) as GlobalActivity;
        if (!parsed.updatedAt || Date.now() - parsed.updatedAt > 120_000) {
          setActiveWork(null);
          return;
        }
        setActiveWork(parsed);
      } catch {
        setActiveWork(null);
      }
    }
    readActiveWork();
    const timer = window.setInterval(readActiveWork, 1500);
    window.addEventListener("storage", readActiveWork);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("storage", readActiveWork);
    };
  }, []);

  async function selectPreset(preset: ModelPreset) {
    if (activeWork) return;
    setBusyPreset(preset.id);
    try {
      const updated = await api.updateModelConfig({ preset_id: preset.id });
      setCurrent(updated);
      api.getModelStatus().then(setCurrent).catch(() => {});
    } finally {
      setBusyPreset(null);
    }
  }

  async function selectById(lineupId: string) {
    if (activeWork) return;
    const preset = findPreset(presets, lineupId);
    if (!preset || preset.availability === "missing") return;
    await selectPreset(preset);
  }

  if (!current) {
    return (
      <div className="rounded-xl border border-line bg-panel p-4">
        <p className="text-[9px] font-bold uppercase tracking-[0.12em] text-muted">Gemma Engine</p>
        <p className="mt-2 text-sm font-semibold text-ink">Backend offline</p>
        <p className="mt-1 text-xs text-secondary">Start the backend to use local model features.</p>
      </div>
    );
  }

  const activeId = detectActive(current.preset_label);
  const switchLocked = Boolean(activeWork);
  const lockTitle = activeWork
    ? `Model switching is locked while ${activeWork.label.toLowerCase()} is running.`
    : undefined;

  // ── Compact mode: Gemma Engine panel ─────────────────────────────────────

  if (compact) {
    return (
      <div className="h-full rounded-xl border border-line bg-panel shadow-material overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-4">
          <div>
            <p className="text-[17px] font-bold leading-tight text-ink">Powered by Gemma 4</p>
            <p className="mt-1 text-[13px] font-medium text-secondary">on-device reading intelligence</p>
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <span className="rounded-full border border-line bg-surface px-2.5 py-1 text-[12px] font-bold text-secondary">GGUF</span>
            <span className="rounded-full bg-accent-soft px-2.5 py-1 text-[12px] font-bold text-accent">MLX</span>
          </div>
        </div>

        {/* Gemma 4 Models — unified list */}
        <div className="px-4 py-4">
          <div className="space-y-2.5">
            {GEMMA4_EDGE.map((m) => {
              const isActive = m.id === activeId;
              const preset = findPreset(presets, m.id);
              const isMissing = preset?.availability === "missing";
              const isBusy = busyPreset === preset?.id;
              const EdgeIcon = m.id === "e2b" ? Zap : Gauge;
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => selectById(m.id)}
                  disabled={switchLocked || isMissing || isBusy || busyPreset !== null}
                  title={lockTitle}
                  className={`w-full flex items-center gap-3 rounded-xl border px-3.5 py-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                    isActive ? "border-accent/25 bg-accent-soft" : "border-line bg-white hover:border-accent/20 hover:bg-[#F8FBFF]"
                  }`}
                >
                  <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border ${
                    isActive ? "border-accent/30 bg-accent-soft text-accent" : "border-line bg-[#F8FAFC] text-muted"
                  }`}>
                    <EdgeIcon size={17} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className={`text-[16px] font-bold ${isActive ? "text-accent" : "text-ink"}`}>{m.name}</span>
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${
                        isActive ? "bg-accent/10 text-accent/80" : "bg-surface text-secondary"
                      }`}>{m.speed}</span>
                    </div>
                    <p className="mt-1 truncate text-[13px] leading-[1.35] text-secondary">{isMissing ? "Install MLX 4-bit model to enable" : m.desc}</p>
                  </div>
                  {isActive && <CheckCircle2 size={15} className="shrink-0 text-accent" />}
                </button>
              );
            })}
            {GEMMA4_FULL.map((m) => {
              const isActive = m.id === activeId;
              const isBusy = busyPreset === findPreset(presets, m.id)?.id;
              const { Icon } = m;
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => selectById(m.id)}
                  disabled={switchLocked || isBusy || busyPreset !== null}
                  title={lockTitle}
                  className={`w-full flex items-center gap-3 rounded-xl border px-3.5 py-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                    isActive ? "border-accent/25 bg-accent-soft" : "border-line bg-white hover:border-accent/20 hover:bg-[#F8FBFF]"
                  }`}
                >
                  <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border ${
                    isActive ? "border-accent/30 bg-accent-soft text-accent" : "border-line bg-white text-muted"
                  }`}>
                    <Icon className="w-[18px] h-[18px]" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className={`text-[16px] font-bold ${isActive ? "text-accent" : "text-ink"}`}>{m.name}</span>
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${
                        isActive ? "bg-accent/10 text-accent/80" : "bg-surface text-secondary"
                      }`}>{m.speed}</span>
                    </div>
                    <p className="mt-1 truncate text-[13px] leading-[1.35] text-secondary">{m.desc}</p>
                  </div>
                  {isActive && <CheckCircle2 size={15} className="shrink-0 text-accent" />}
                </button>
              );
            })}
          </div>
        </div>

      </div>
    );
  }

  // ── Full mode: preset switcher ────────────────────────────────────────────

  return (
    <div className="rounded-xl border border-line bg-panel p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[9px] font-bold uppercase tracking-[0.14em] text-muted">Gemma Engine</p>
          <p className="mt-1 text-base font-bold text-ink">{current.preset_label}</p>
        </div>
        <span className="shrink-0 rounded-full bg-accent-soft px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-accent">
          {current.provider}
        </span>
      </div>

      <div className="mt-4">
        <button
          type="button"
          onClick={() => setShowPresets((v) => !v)}
          disabled={switchLocked}
          title={lockTitle}
          className="flex w-full items-center justify-between gap-2 rounded-md border border-line px-3 py-2 text-sm font-semibold text-secondary transition-colors hover:bg-subtle hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
        >
          {switchLocked ? "Model locked during active work" : "Change model"}
          {showPresets ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
        {showPresets ? (
          <div className="mt-2 space-y-1.5">
            {presets
              .filter((p) => p.runtime !== "remote")
              .map((preset) => (
                <PresetButton
                  key={preset.id}
                  preset={preset}
                  selected={current.preset_id === preset.id}
                  busy={switchLocked || busyPreset !== null}
                  lockedReason={lockTitle}
                  onSelect={selectPreset}
                />
              ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function PresetButton({
  preset,
  selected,
  busy,
  lockedReason,
  onSelect
}: {
  preset: ModelPreset;
  selected: boolean;
  busy: boolean;
  lockedReason?: string;
  onSelect: (preset: ModelPreset) => void;
}) {
  const Icon = runtimeIcon[preset.runtime];
  const disabled = preset.availability === "missing";
  return (
    <button
      type="button"
      onClick={() => onSelect(preset)}
      disabled={disabled || busy}
      title={lockedReason}
      className={`w-full rounded-lg border p-3 text-left transition-colors ${
        selected ? "border-accent/30 bg-accent-soft" : "border-line bg-white hover:bg-surface"
      } disabled:cursor-not-allowed disabled:opacity-50`}
    >
      <div className="flex items-start gap-2.5">
        <Icon size={15} className={`mt-0.5 shrink-0 ${selected ? "text-accent" : "text-muted"}`} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-semibold text-ink">{preset.label}</p>
            {selected ? <CheckCircle2 size={14} className="text-accent" /> : null}
          </div>
          <p className="mt-0.5 line-clamp-2 text-xs leading-4 text-secondary">{preset.description}</p>
          <div className="mt-1.5 flex flex-wrap gap-1 text-[10px]">
            <span className="rounded-full bg-surface px-1.5 py-0.5 text-secondary">{preset.size}</span>
            <span className="rounded-full bg-surface px-1.5 py-0.5 text-secondary">{preset.speed}</span>
            <span className={`rounded-full px-1.5 py-0.5 ${
              preset.availability === "ready" ? "bg-green-50 text-green-700"
              : preset.availability === "external" ? "bg-amber-50 text-amber-700"
              : "bg-red-50 text-red-700"
            }`}>
              {preset.availability}
            </span>
          </div>
        </div>
      </div>
    </button>
  );
}
