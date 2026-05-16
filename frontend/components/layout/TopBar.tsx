"use client";

import { useEffect, useState } from "react";

type GlobalActivity = {
  label: string;
  detail: string;
  updatedAt: number;
};

export function TopBar() {
  const [activity, setActivity] = useState<GlobalActivity | null>(null);

  useEffect(() => {
    function read() {
      try {
        const raw = window.localStorage.getItem("gemmalens:active-task");
        if (!raw) {
          setActivity(null);
          return;
        }
        const parsed = JSON.parse(raw) as GlobalActivity;
        if (!parsed.updatedAt || Date.now() - parsed.updatedAt > 20_000) {
          setActivity(null);
          return;
        }
        setActivity(parsed);
      } catch {
        setActivity(null);
      }
    }
    read();
    const timer = window.setInterval(read, 1500);
    window.addEventListener("storage", read);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("storage", read);
    };
  }, []);

  if (!activity) return null;

  return (
    <div className="sticky top-0 z-30 border-b border-blue-200 bg-blue-50 px-4 py-2 text-sm shadow-sm">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-2 text-accent">
        <div className="flex min-w-0 items-center gap-2 font-semibold">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-accent" />
          <span>{activity.label}</span>
        </div>
        <p className="min-w-0 text-xs font-medium text-neutral-700">{activity.detail}</p>
      </div>
    </div>
  );
}
