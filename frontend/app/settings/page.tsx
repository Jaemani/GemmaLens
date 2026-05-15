import { SettingsClient } from "./SettingsClient";
import { api } from "@/lib/api";
import type { UserProfile } from "@/lib/types";

export default async function SettingsPage() {
  let profile: UserProfile | null = null;
  let error: string | null = null;

  try {
    profile = await api.getProfile();
  } catch (err) {
    error = err instanceof Error ? err.message : "Could not load profile.";
  }

  return <SettingsClient initialProfile={profile} initialError={error} />;
}
