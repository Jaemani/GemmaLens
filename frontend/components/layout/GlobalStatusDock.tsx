"use client";

import { Activity, ChevronDown, ChevronUp, Circle, Cpu } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
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
  const [expanded, setExpanded] = useState(true);
  const idleDetail = model ? `${model.provider} runtime` : "No active document, video, or translation task";
  const aliveTone = alive === null ? "text-neutral-500" : alive ? "text-green-700" : "text-red-700";

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
        if (!parsed.updatedAt || Date.now() - parsed.updatedAt > 120_000) {
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

  function openActivity() {
    if (activity?.href) router.push(activity.href);
  }

  return (
    <aside
      className={`fixed bottom-3 right-3 z-40 rounded-lg border border-line bg-panel/95 text-[11px] shadow-material backdrop-blur ${
        expanded ? "w-[min(260px,calc(100vw-1.5rem))]" : "w-[min(156px,calc(100vw-1.5rem))]"
      }`}
    >
      <div className="flex items-center justify-between gap-2 px-3 py-2">
        <button type="button" onClick={openActivity} className="flex min-w-0 items-center gap-2 text-left font-semibold text-ink disabled:cursor-default" disabled={!activity?.href}>
          <Activity size={13} className={activity ? "shrink-0 animate-pulse text-accent" : "shrink-0 text-neutral-500"} />
          <span className="truncate">{activity?.label ?? "Idle"}</span>
        </button>
        <div className="flex shrink-0 items-center gap-2">
          <div className={`flex items-center gap-1 font-semibold ${aliveTone}`}>
            <Circle size={7} fill="currentColor" className={alive && !activity ? "animate-pulse" : ""} />
            {expanded ? (alive === null ? "Check" : alive ? "Alive" : "Off") : null}
          </div>
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            className="inline-flex h-6 w-6 items-center justify-center rounded-md border border-line hover:bg-surface"
            aria-label={expanded ? "Collapse runtime status" : "Expand runtime status"}
          >
            {expanded ? <ChevronDown size={13} /> : <ChevronUp size={13} />}
          </button>
        </div>
      </div>
      {expanded ? (
        <div className="border-t border-line px-3 py-2">
          <div className="flex items-center gap-2 font-semibold text-ink">
            <Cpu size={13} />
            <span className="truncate">{model?.preset_label ?? "Model unknown"}</span>
          </div>
          <button
            type="button"
            onClick={openActivity}
            disabled={!activity?.href}
            className="mt-2 w-full min-w-0 text-left text-neutral-600 disabled:cursor-default"
          >
            <span className="block truncate">{activity?.detail ?? idleDetail}</span>
            {activity?.href ? <span className="mt-1 block font-semibold text-accent">Open active work</span> : null}
          </button>
        </div>
      ) : null}
    </aside>
  );
}
