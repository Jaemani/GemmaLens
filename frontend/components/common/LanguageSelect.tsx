"use client";

import { useMemo, useState } from "react";
import { LANGUAGE_OPTIONS } from "@/lib/languages";

export function LanguageSelect({
  label,
  value,
  onChange,
  disabled
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return LANGUAGE_OPTIONS;
    return LANGUAGE_OPTIONS.filter((language) => language.name.toLowerCase().includes(normalized) || language.code.includes(normalized)).slice(0, 50);
  }, [query]);

  return (
    <div>
      <label className="text-sm font-semibold text-neutral-600" htmlFor={`${label}-language-search`}>{label}</label>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange(value)}
        className="mt-2 flex w-full items-center justify-between rounded-md border border-accent bg-blue-50 px-3 py-2 text-left text-sm font-semibold text-accent disabled:opacity-50"
      >
        <span>{value}</span>
        <span className="text-xs uppercase text-accent">selected</span>
      </button>
      <input
        id={`${label}-language-search`}
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        disabled={disabled}
        placeholder="Search language"
        className="mt-3 w-full rounded-md border border-line px-3 py-2 text-sm disabled:opacity-50"
      />
      <div className="mt-3 max-h-64 overflow-y-auto rounded-md border border-line bg-white p-2">
        {filtered.map((language) => (
          <button
            key={language.code}
            type="button"
            disabled={disabled}
            onClick={() => onChange(language.name)}
            className={`mb-1 flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm ${
              value === language.name ? "bg-blue-50 font-semibold text-accent" : "hover:bg-surface"
            } disabled:opacity-50`}
          >
            <span>{language.name}</span>
            <span className="text-xs uppercase text-neutral-400">{language.code}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
