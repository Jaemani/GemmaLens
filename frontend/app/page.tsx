import Link from "next/link";
import { BookMarked, FileQuestion, FileText, Languages, Video } from "lucide-react";
import { ModelStatusCard } from "@/components/common/ModelStatusCard";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import type { ModelStatus } from "@/lib/types";

export default async function DashboardPage() {
  let modelStatus: ModelStatus | null = null;
  try {
    modelStatus = await api.getModelStatus();
  } catch {
    modelStatus = null;
  }

  return (
    <AppShell>
      <div className="space-y-5">
        <section className="rounded-lg border border-line bg-panel p-5 shadow-material">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase text-accent">Reading workspace</p>
              <h1 className="mt-2 text-2xl font-semibold">PaperLens</h1>
            </div>
            <div className="flex flex-wrap gap-2">
              <PrimaryLink href="/documents" label="Analyze document" />
              <SecondaryLink href="/video" label="Video transcript" />
              <SecondaryLink href="/quiz" label="Quiz" />
            </div>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="grid gap-4 sm:grid-cols-2">
            <ActionCard href="/documents" icon={<FileText size={19} />} title="Documents" detail="Upload PDF/text or paste a focused excerpt." />
            <ActionCard href="/video" icon={<Video size={19} />} title="Video" detail="Fetch captions and analyze scenes or transcripts." />
            <ActionCard href="/tools" icon={<Languages size={19} />} title="Translate" detail="Short passage translation workspace." />
            <ActionCard href="/quiz" icon={<FileQuestion size={19} />} title="Quiz maker" detail="Build cached review prompts from analyzed sources." />
          </div>
          <ModelStatusCard status={modelStatus} />
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          <Stat icon={<FileText size={18} />} label="Pipeline" value="Extract -> analyze -> save" />
          <Stat icon={<BookMarked size={18} />} label="Dictionary" value="Terms, phrases, structures" />
          <Stat icon={<FileQuestion size={18} />} label="Review" value="Quiz drafts from analysis" />
        </section>
      </div>
    </AppShell>
  );
}

function PrimaryLink({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href} className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white">
      {label}
    </Link>
  );
}

function SecondaryLink({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href} className="rounded-md border border-line px-4 py-2 text-sm font-semibold text-ink hover:bg-surface">
      {label}
    </Link>
  );
}

function ActionCard({ href, icon, title, detail }: { href: string; icon: React.ReactNode; title: string; detail: string }) {
  return (
    <Link href={href} className="rounded-lg border border-line bg-panel p-4 shadow-material transition hover:bg-surface">
      <div className="text-accent">{icon}</div>
      <p className="mt-3 font-semibold">{title}</p>
      <p className="mt-1 text-sm leading-6 text-neutral-600">{detail}</p>
    </Link>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-panel p-4 shadow-material">
      <div className="flex items-center gap-3">
        <div className="text-accent">{icon}</div>
        <div>
          <p className="text-xs font-semibold uppercase text-neutral-500">{label}</p>
          <p className="mt-1 text-sm font-semibold">{value}</p>
        </div>
      </div>
    </div>
  );
}
