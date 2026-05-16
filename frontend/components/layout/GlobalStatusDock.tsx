"use client";

import { Activity, Circle, Cpu } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ModelStatus } from "@/lib/types";

type GlobalActivity = {
  label: string;
  detail: string;
  updatedAt: number;
};

export function GlobalStatusDock() {
  const [alive, setAlive] = useState<boolean | null>(null);
  const [model, setModel] = useState<ModelStatus | null>(null);
  const [activity, setActivity] = useState<GlobalActivity | null>(null);
  const idleDetail = model ? `${model.provider} runtime` : "No active document, video, or translation task";

  useEffect(() => {
    let cancelled = false;

    async function pollBackend() {
      try {
        const [health, status] = await Promise.all([api.health(), api.getModelStatus()]);
        if (cancelled) return;
        setAlive(health.status === "ok");
        setModel(status);
      } catch {
        if (cancelled) return;
        setAlive(false);
        setModel(null);
      }
    }

    pollBackend();
    const timer = window.setInterval(pollBackend, 8000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    function readActivity() {
      try {
        const raw = window.localStorage.getItem("gemmalens:active-task");
        if (!raw) {
          setActivity(null);
          return;
        }
        const parsed = JSON.parse(raw) as GlobalActivity;
        if (!parsed.updatedAt || Date.now() - parsed.updatedAt > 30_000) {
          setActivity(null);
          return;
        }
        setActivity(parsed);
      } catch {
        setActivity(null);
      }
    }

    readActivity();
    const timer = window.setInterval(readActivity, 1500);
    window.addEventListener("storage", readActivity);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("storage", readActivity);
    };
  }, []);

  return (
    <aside className="fixed bottom-4 right-4 z-40 w-[min(360px,calc(100vw-2rem))] rounded-lg border border-line bg-panel/95 p-3 text-xs shadow-material backdrop-blur">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 font-semibold text-ink">
          <Cpu size={15} />
          <span>{model?.preset_label ?? "Model unknown"}</span>
        </div>
        <div className={`flex items-center gap-1 font-semibold ${alive ? "text-green-700" : "text-red-700"}`}>
          <Circle size={9} fill="currentColor" />
          {alive === null ? "Checking" : alive ? "Alive" : "Offline"}
        </div>
      </div>
      <div className="mt-2 flex items-start gap-2 border-t border-line pt-2">
        <Activity size={14} className={activity ? "mt-0.5 shrink-0 animate-pulse text-accent" : "mt-0.5 shrink-0 text-neutral-500"} />
        <div className="min-w-0">
          <p className="font-semibold text-ink">{activity?.label ?? "Idle"}</p>
          <p className="mt-0.5 truncate text-neutral-600">{activity?.detail ?? idleDetail}</p>
        </div>
      </div>
    </aside>
  );
}
