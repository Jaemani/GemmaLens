"use client";

import { useEffect, useState } from "react";
import { LanguageSelect } from "@/components/common/LanguageSelect";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import type { UserProfile } from "@/lib/types";

const levels: UserProfile["target_level"][] = ["B1", "B2", "C1", "C2", "domain-heavy", "unknown"];

export default function SettingsPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getProfile()
      .then((loadedProfile) => {
        setProfile(loadedProfile);
        setError(null);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Could not load profile.");
      });
  }, []);

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
      <div className="mb-6">
        <p className="text-sm font-semibold uppercase text-accent">Local learner profile</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Settings</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-700">
          Set the language you are learning and the language used for explanations. These settings prepare the pipeline for multilingual prompts and study memory.
        </p>
      </div>

      {error ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm leading-6 text-amber-900 shadow-material">
          {error}
        </div>
      ) : !profile ? (
        <div className="rounded-2xl border border-line bg-panel p-6 shadow-material">Loading profile...</div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <section className="rounded-2xl border border-line bg-panel p-6 shadow-material">
            <h2 className="text-xl font-semibold">Language pair</h2>
            <Field label="Learning language">
              <LanguageSelect
                label="Search learning language"
                value={profile.learning_language}
                onChange={(learning_language) => save({ learning_language })}
                disabled={busy}
              />
            </Field>
            <Field label="Explanation language">
              <LanguageSelect
                label="Search explanation language"
                value={profile.support_language}
                onChange={(support_language) => save({ support_language })}
                disabled={busy}
              />
            </Field>
            <p className="mt-4 rounded-2xl bg-surface p-4 text-sm leading-6 text-neutral-700">
              Gemma-family docs describe broad multilingual support across 140+ languages. Quality may vary by language pair, model size, and prompt.
            </p>
          </section>

          <section className="rounded-2xl border border-line bg-panel p-6 shadow-material">
            <h2 className="text-xl font-semibold">Reading level</h2>
            <Field label="Target level">
              <Segmented items={levels} value={profile.target_level} onChange={(target_level) => save({ target_level })} disabled={busy} />
            </Field>
            <div className="mt-5 rounded-2xl bg-surface p-4 text-sm leading-6 text-neutral-700">
              Fresh users start with a simple profile. GemmaLens can later infer learning focus from saved terms, viewed items, and repeated document domains.
            </div>
          </section>
        </div>
      )}
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
  disabled
}: {
  items: readonly T[];
  value: T;
  onChange: (value: T) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <button
          key={item}
          disabled={disabled}
          onClick={() => onChange(item)}
          className={`rounded-full border px-3 py-2 text-sm font-medium ${value === item ? "border-accent bg-blue-50 text-accent" : "border-line bg-white hover:bg-surface"} disabled:opacity-50`}
        >
          {item}
        </button>
      ))}
    </div>
  );
}
