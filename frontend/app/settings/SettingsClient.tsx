"use client";

import { useState } from "react";
import { LanguageSelect } from "@/components/common/LanguageSelect";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import type { UserProfile } from "@/lib/types";

const levels: UserProfile["target_level"][] = ["B1", "B2", "C1", "C2", "domain-heavy", "unknown"];

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
          <p className="text-sm font-semibold text-accent">Local learner profile</p>
          <h1 className="mt-2 text-2xl font-semibold text-ink">Settings</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-700">
            Choose the language you are learning, the language used for explanations, and the level GemmaLens should assume when it builds reading support.
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
              <p className="mt-4 rounded-lg bg-surface p-4 text-sm leading-6 text-neutral-700">
                Language quality depends on the selected model and pair. The profile is local and can later be used to personalize saved terms, review timing, and explanation style.
              </p>
            </section>

            <section className="rounded-lg border border-line bg-panel p-5 shadow-material">
              <h2 className="text-xl font-semibold">Reading level</h2>
              <Field label="Target level">
                <Segmented items={levels} value={profile.target_level} onChange={(target_level) => save({ target_level })} disabled={busy} />
              </Field>
              <div className="mt-5 rounded-lg bg-surface p-4 text-sm leading-6 text-neutral-700">
                The analysis should surface unfamiliar high-value terms, sentence structure, and domain cues without treating every unknown word as equally important.
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
          type="button"
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
