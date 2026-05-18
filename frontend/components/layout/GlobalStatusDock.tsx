"use client";

import { Activity, Circle, Cpu } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { ModelStatus } from "@/lib/types";

type GlobalActivity = {
  label: string;
  detail: string;
  href?: string;
  updatedAt: number;
};

export function GlobalStatusDock() {
  const router = useRouter();
  const [alive, setAlive] = useState<boolean | null>(null);
  const [model, setModel] = useState<ModelStatus | null>(null);
  const [activity, setActivity] = useState<GlobalActivity | null>(null);
  const activityRef = useRef<GlobalActivity | null>(null);
  const healthMissesRef = useRef(0);
  const lastAliveAtRef = useRef<number | null>(null);
  const idleDetail = "No active work";

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const health = await api.health();
        if (cancelled) return;
        if (health.status === "ok") {
          healthMissesRef.current = 0;
          lastAliveAtRef.current = Date.now();
          setAlive(true);
        }
      } catch {
        if (cancelled) return;
        healthMissesRef.current += 1;
        const recentlyAlive = lastAliveAtRef.current ? Date.now() - lastAliveAtRef.current < 45_000 : false;
        if (activityRef.current || recentlyAlive || healthMissesRef.current < 3) {
          setAlive((current) => current ?? true);
        } else {
          setAlive(false);
        }
      }

      try {
        const status = await api.getModelStatus();
        if (cancelled) return;
        setModel(status);
      } catch {
        // During local analysis the model runtime can be busy even while the
        // backend is alive. Keep the last known model instead of flickering.
      }
    }
    poll();
    const timer = window.setInterval(poll, 8000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, []);

  useEffect(() => {
    function readActivity() {
      try {
        const raw = window.localStorage.getItem("gemmalens:active-task");
        if (!raw) {
          activityRef.current = null;
          setActivity(null);
          return;
        }
        const parsed = JSON.parse(raw) as GlobalActivity;
        if (!parsed.updatedAt || Date.now() - parsed.updatedAt > 600_000) {
          activityRef.current = null;
          setActivity(null);
          return;
        }
        activityRef.current = parsed;
        setActivity(parsed);
      } catch {
        activityRef.current = null;
        setActivity(null);
      }
    }
    readActivity();
    const timer = window.setInterval(readActivity, 1500);
    window.addEventListener("storage", readActivity);
    return () => { window.clearInterval(timer); window.removeEventListener("storage", readActivity); };
  }, []);

  function openActivity() {
    if (activity?.href) router.push(activity.href);
  }

  const backendTone = alive === null ? "text-amber-600" : alive ? "text-green-600" : "text-red-500";
  const backendLabel = alive === null ? "Checking" : alive ? "Alive" : "Off";
  const modelLabel = model?.preset_label ?? (alive === null ? "Checking model..." : alive ? "Model status loading" : "Model unavailable");

  return (
    <aside className="rounded-lg border border-line bg-surface text-xs">
      {/* Row 1: activity + backend status */}
      <div className="flex items-center justify-between gap-2 px-3 py-2">
        <button
          type="button"
          onClick={openActivity}
          disabled={!activity?.href}
          className="flex min-w-0 items-center gap-2 text-left text-ink disabled:cursor-default"
        >
          <Activity
            size={14}
            className={activity ? "shrink-0 animate-pulse text-accent" : "shrink-0 text-muted"}
          />
          <span className="truncate font-bold">{activity?.label ?? "Ready"}</span>
        </button>
        <div className={`flex shrink-0 items-center gap-1.5 text-[12px] ${backendTone}`}>
          <Circle size={7} fill="currentColor" className={alive ? "animate-pulse" : ""} />
          <span className="font-bold">{backendLabel}</span>
        </div>
      </div>

      {/* Row 2: model + activity detail */}
      <div className="border-t border-line px-3 py-2">
        <div className="flex items-center gap-2 font-semibold text-ink">
          <Cpu size={14} className="shrink-0 text-muted" />
          <span className="truncate">{modelLabel}</span>
        </div>
        <button
          type="button"
          onClick={openActivity}
          disabled={!activity?.href}
          className="mt-1.5 w-full min-w-0 text-left text-[12px] font-medium text-secondary disabled:cursor-default"
        >
          <span className="block truncate">{activity?.detail ?? idleDetail}</span>
          {activity?.href ? (
            <span className="mt-0.5 block font-semibold text-accent">Open active work</span>
          ) : null}
        </button>
      </div>
    </aside>
  );
}
