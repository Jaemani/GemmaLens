import Link from "next/link";
import { ArrowRight, BookMarked, Cpu, FileText, Languages, PlayCircle, Video, WifiOff } from "lucide-react";
import { ModelStatusCard } from "@/components/common/ModelStatusCard";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import type { DocumentListItem, ModelStatus } from "@/lib/types";

export default async function DashboardPage() {
  let modelStatus: ModelStatus | null = null;
  let documents: DocumentListItem[] = [];
  try {
    modelStatus = await api.getModelStatus();
  } catch {
    modelStatus = null;
  }
  try {
    documents = await api.listDocuments();
  } catch {
    documents = [];
  }
  const recentDocuments = documents.filter((document) => !isVideoSource(document.source_type));

  return (
    <AppShell>
      <div className="space-y-5">
        <section className="grid items-stretch gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="rounded-lg border border-line bg-panel p-6 shadow-material">
            <p className="text-sm font-semibold text-accent">GemmaLens</p>
            <h1 className="mt-2 max-w-3xl text-3xl font-semibold leading-tight text-ink">
              Multimodal Language Learning from Any Content
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-600">
              Offline-first reading support for papers, PDFs, videos, and short passages. GemmaLens extracts the language signals that matter for the learner, not just a one-time translation.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <Signal icon={<WifiOff size={15} />} label="Offline-ready" />
              <Signal icon={<Cpu size={15} />} label="Edge-device friendly" />
              <Signal icon={<BookMarked size={15} />} label="Personalized study memory" />
              <Signal icon={<Languages size={15} />} label="Translate when useful" />
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              <PrimaryAction href="/documents" label="Analyze a document" icon={<FileText size={17} />} />
              <SecondaryAction href="/video" label="Study a video" icon={<Video size={17} />} />
            </div>
          </div>
          <ModelStatusCard status={modelStatus} compact />
        </section>

        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-semibold">Recent documents</h2>
              <Link href="/documents" className="inline-flex items-center gap-1 text-sm font-semibold text-accent">
                Open <ArrowRight size={15} />
              </Link>
            </div>
            <div className="mt-3 divide-y divide-line">
              {recentDocuments.slice(0, 5).map((document) => (
                <Link key={document.id} href={`/analysis/${document.id}`} className="block rounded-md py-3 text-sm hover:bg-surface">
                  <span className="flex items-center justify-between gap-3">
                    <span className="min-w-0 truncate font-semibold text-ink">{document.title}</span>
                    <DocumentProgressLabel document={document} />
                  </span>
                  <span className="mt-1 line-clamp-1 block text-neutral-600">{document.preview}</span>
                </Link>
              ))}
              {!recentDocuments.length ? (
                <div className="grid min-h-32 place-items-center rounded-md bg-surface px-4 py-6 text-center text-sm leading-6 text-neutral-600">
                  <p>No documents yet. Add a PDF, paper excerpt, or transcript to see learning objects here.</p>
                </div>
              ) : null}
            </div>
          </div>

          <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
            <h2 className="font-semibold">Current learning loop</h2>
            <div className="mt-4 space-y-3">
              <LoopStep label="1" title="Extract" text="PDF, text, markdown, or transcript" />
              <LoopStep label="2" title="Analyze" text="Terms, phrases, syntax, summaries" />
              <LoopStep label="3" title="Review" text="Save, translate, quiz, revisit" />
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          <Capability icon={<FileText size={18} />} title="Document-aware" text="Prioritizes vocabulary and structures by source context and domain." />
          <Capability icon={<BookMarked size={18} />} title="Learner-fitted" text="Uses level, language pair, and saved items to guide what to show." />
          <Capability icon={<PlayCircle size={18} />} title="Multimodal path" text="Documents first, video transcripts next, translation and quiz as tools." />
        </section>
      </div>
    </AppShell>
  );
}

function isVideoSource(sourceType: string) {
  return sourceType === "transcript" || sourceType === "video_segment";
}

function DocumentProgressLabel({ document }: { document: DocumentListItem }) {
  const total = document.total_sections ?? 0;
  const analyzed = document.analyzed_sections ?? 0;
  if (total <= 1) return analyzed > 0 ? <span className="shrink-0 text-xs font-semibold text-emerald-700">Ready</span> : null;
  if (analyzed >= total) return <span className="shrink-0 text-xs font-semibold text-emerald-700">Complete</span>;
  if (analyzed > 0) return <span className="shrink-0 text-xs font-semibold text-amber-700">{analyzed}/{total}</span>;
  return <span className="shrink-0 text-xs font-semibold text-neutral-500">Not studied</span>;
}

function Signal({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-accent">
      {icon}
      {label}
    </span>
  );
}

function LoopStep({ label, title, text }: { label: string; title: string; text: string }) {
  return (
    <div className="flex items-start gap-3 rounded-md bg-surface px-3 py-3">
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-semibold text-accent">
        {label}
      </span>
      <span>
        <span className="block text-sm font-semibold text-ink">{title}</span>
        <span className="mt-1 block text-sm text-neutral-600">{text}</span>
      </span>
    </div>
  );
}

function PrimaryAction({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <Link href={href} className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
      {icon}
      {label}
    </Link>
  );
}

function SecondaryAction({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <Link href={href} className="inline-flex items-center gap-2 rounded-md border border-line bg-white px-4 py-2 text-sm font-semibold text-ink hover:bg-surface">
      {icon}
      {label}
    </Link>
  );
}

function Capability({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return (
    <div className="rounded-lg border border-line bg-panel p-4 shadow-material">
      <div className="flex items-start gap-3">
        <div className="rounded-md bg-blue-50 p-2 text-accent">{icon}</div>
        <div>
          <h3 className="font-semibold">{title}</h3>
          <p className="mt-1 text-sm leading-6 text-neutral-600">{text}</p>
        </div>
      </div>
    </div>
  );
}
