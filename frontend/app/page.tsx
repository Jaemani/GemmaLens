import Link from "next/link";
import { BookMarked, Cpu, FileQuestion, FileText, Languages, Video, WifiOff } from "lucide-react";
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
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-3xl">
              <p className="text-sm font-semibold uppercase text-accent">GemmaLens</p>
              <h1 className="mt-2 text-2xl font-semibold">Multimodal Language Learning from Any Content</h1>
              <p className="mt-3 text-sm leading-6 text-neutral-600">
                Turn papers, PDFs, video transcripts, and short passages into personalized language-learning material with local Gemma models.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Signal icon={<WifiOff size={15} />} label="Offline-ready" />
                <Signal icon={<Cpu size={15} />} label="Fast edge inference" />
                <Signal icon={<BookMarked size={15} />} label="Personalized dictionary" />
                <Signal icon={<Languages size={15} />} label="Translate + learn" />
              </div>
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
          <Stat icon={<FileText size={18} />} label="Any content" value="Document, video, text" />
          <Stat icon={<BookMarked size={18} />} label="Personal fit" value="Terms, phrases, structures" />
          <Stat icon={<FileQuestion size={18} />} label="Edge workflow" value="Extract -> analyze -> review" />
        </section>
      </div>
    </AppShell>
  );
}

function Signal({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-accent">
      {icon}
      {label}
    </span>
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
