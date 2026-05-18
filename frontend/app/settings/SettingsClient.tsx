"use client";

import { useState } from "react";
import { LanguageSelect } from "@/components/common/LanguageSelect";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import type { UserProfile } from "@/lib/types";

const levels: UserProfile["target_level"][] = ["B1", "B2", "C1", "C2", "domain-heavy", "unknown"];
const levelDetails: Record<UserProfile["target_level"], string> = {
  B1: "Shows more core vocabulary, simpler meanings, and sentence support for academic basics.",
  B2: "Balances domain vocabulary with reusable academic phrases and longer sentence guidance.",
  C1: "Prioritizes nuance, argument structure, and expressions common in research writing.",
  C2: "Filters for precision, field-specific phrasing, dense concepts, and paper-level reasoning.",
  "domain-heavy": "Assumes grammar is manageable and focuses on specialist concepts and terminology.",
  unknown: "Lets GemmaLens choose the level from the source text when you do not want a fixed target.",
};
const defaultProfile: Partial<UserProfile> = {
  learning_language: "English",
  support_language: "Korean",
  target_level: "C2",
  auto_analyze_documents: true,
};

export function SettingsClient({
  initialProfile,
  initialError
}: {
  initialProfile: UserProfile | null;
  initialError: string | null;
}) {
  const [profile, setProfile] = useState<UserProfile | null>(initialProfile);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(initialError);

  async function retryLoad() {
    setBusy(true);
    setError(null);
    try {
      const loadedProfile = await api.getProfile();
      setProfile(loadedProfile);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load profile.");
    } finally {
      setBusy(false);
    }
  }

  async function save(updates: Partial<UserProfile>) {
    if (!profile) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.updateProfile({ ...updates, onboarding_completed: true });
      setProfile(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <div className="w-full">
        <div className="mb-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-2xl font-semibold text-ink">Settings</h1>
            {profile ? (
              <button
                type="button"
                onClick={() => save(defaultProfile)}
                disabled={busy}
                className="rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:border-accent/40 hover:text-accent disabled:opacity-50"
              >
                Reset to defaults
              </button>
            ) : null}
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-700">
            Choose the language pair, reading level, and background preparation behavior used by the current paper and video analysis pipeline.
          </p>
        </div>

        {error && !profile ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-5 text-sm leading-6 text-amber-900 shadow-material">
            <p>{error}</p>
            <button
              type="button"
              onClick={retryLoad}
              disabled={busy}
              className="mt-3 rounded-md border border-amber-300 bg-white px-3 py-2 text-sm font-semibold text-amber-900 disabled:opacity-60"
            >
              {busy ? "Retrying..." : "Retry"}
            </button>
          </div>
        ) : profile ? (
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <section className="rounded-lg border border-line bg-panel p-5 shadow-material">
              <h2 className="text-xl font-semibold">Language pair</h2>
              <div className="mt-5">
                <LanguageSelect
                  label="Learning language"
                  value={profile.learning_language}
                  onChange={(learning_language) => save({ learning_language })}
                  disabled={busy}
                />
              </div>
              <div className="mt-5">
                <LanguageSelect
                  label="Explanation language"
                  value={profile.support_language}
                  onChange={(support_language) => save({ support_language })}
                  disabled={busy}
                />
              </div>
              <p className="mt-4 rounded-lg bg-surface p-4 text-sm leading-6 text-neutral-700">
                These languages are passed into document and subtitle analysis, including native-language glosses and learner explanations.
              </p>
            </section>

            <section className="rounded-lg border border-line bg-panel p-5 shadow-material">
              <h2 className="text-xl font-semibold">Reading level</h2>
              <Field label="Target level">
                <Segmented
                  items={levels}
                  value={profile.target_level}
                  onChange={(target_level) => save({ target_level })}
                  disabled={busy}
                  labelFor={levelLabel}
                />
              </Field>
              <div className="mt-4 rounded-lg border border-accent/15 bg-blue-50/50 p-4">
                <p className="text-sm font-semibold text-ink">{levelLabel(profile.target_level)} reading target</p>
                <p className="mt-1 text-sm leading-6 text-neutral-700">{levelDetails[profile.target_level]}</p>
              </div>
              <p className="mt-3 text-xs leading-5 text-neutral-500">
                Used by paper and video analysis to tune which terms, concepts, and academic phrases are worth showing.
              </p>
            </section>

            <section className="rounded-lg border border-line bg-panel p-5 shadow-material xl:col-span-2">
              <h2 className="text-xl font-semibold">Preparation</h2>
              <div className="mt-5 grid gap-3">
                <ToggleRow
                  title="Prepare paper sections automatically"
                  detail="Open the first page quickly, then prepare remaining lessons in the background."
                  checked={profile.auto_analyze_documents}
                  disabled={busy}
                  onChange={() => save({ auto_analyze_documents: !profile.auto_analyze_documents })}
                />
              </div>
            </section>
          </div>
        ) : (
          <div className="rounded-lg border border-line bg-panel p-5 shadow-material">Loading profile...</div>
        )}
      </div>
    </AppShell>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mt-5">
      <p className="mb-2 text-sm font-semibold text-neutral-600">{label}</p>
      {children}
    </div>
  );
}

function Segmented<T extends string>({
  items,
  value,
  onChange,
  disabled,
  labelFor = String
}: {
  items: readonly T[];
  value: T;
  onChange: (value: T) => void;
  disabled?: boolean;
  labelFor?: (value: T) => string;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <button
          key={item}
          type="button"
          disabled={disabled}
          onClick={() => onChange(item)}
          className={`rounded-full border px-3 py-2 text-sm font-medium ${value === item ? "border-accent bg-blue-50 text-accent" : "border-line bg-white hover:bg-surface"} disabled:opacity-50`}
        >
          {labelFor(item)}
        </button>
      ))}
    </div>
  );
}

function ToggleRow({
  title,
  detail,
  checked,
  disabled,
  onChange
}: {
  title: string;
  detail: string;
  checked: boolean;
  disabled?: boolean;
  onChange: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-surface p-4">
      <div className="max-w-md">
        <p className="text-sm font-semibold text-ink">{title}</p>
        <p className="mt-1 text-sm leading-6 text-neutral-700">{detail}</p>
      </div>
      <button
        type="button"
        onClick={onChange}
        disabled={disabled}
        className={`min-w-24 rounded-md border px-4 py-2 text-sm font-semibold ${
          checked ? "border-accent bg-blue-50 text-accent" : "border-line bg-white text-neutral-700"
        } disabled:opacity-50`}
      >
        {checked ? "On" : "Off"}
      </button>
    </div>
  );
}

function levelLabel(value: string) {
  if (value === "domain-heavy") return "Domain-heavy";
  if (value === "unknown") return "Auto";
  return value;
}
