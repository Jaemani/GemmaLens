import Image from "next/image";
import Link from "next/link";
import { ArrowRight, BookOpen, FileText, Map, Video } from "lucide-react";
import { ModelStatusCard } from "@/components/common/ModelStatusCard";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import { cleanDocumentPreview, displayableDocuments, documentProgressText, isVideoSource } from "@/lib/documentDisplay";
import type { DictionaryItem, DocumentListItem, ModelStatus } from "@/lib/types";

export default async function DashboardPage() {
  let modelStatus: ModelStatus | null = null;
  let documents: DocumentListItem[] = [];
  let dictionaryItems: DictionaryItem[] = [];

  await Promise.allSettled([
    api.getModelStatus().then((s) => { modelStatus = s; }).catch(() => {}),
    api.listDocuments().then((d) => { documents = d; }).catch(() => {}),
    api.listDictionary().then((d) => { dictionaryItems = d; }).catch(() => {}),
  ]);

  const allDocs = displayableDocuments(documents);
  const paperDocs = allDocs.filter((d) => !isVideoSource(d.source_type));
  const recentDocs = paperDocs.slice(0, 5);
  const topDoc = recentDocs[0] ?? null;

  const totalAnalyzed = documents.reduce((sum, d) => sum + (d.analyzed_sections ?? 0), 0);
  const termItems = dictionaryItems.filter((d) => d.item_type === "term");
  const phraseItems = dictionaryItems.filter((d) => d.item_type === "phrase");

  const topDocTerms = topDoc ? dictionaryItems.filter((d) => d.document_id === topDoc.id) : [];
  const topDocAnalyzed = topDoc?.analyzed_sections ?? 0;
  const topDocTotal = topDoc?.total_sections ?? 0;
  const topDocProgress = topDocTotal > 0 ? Math.round((topDocAnalyzed / topDocTotal) * 100) : 0;

  const reviewTotal = termItems.length + phraseItems.length;
  const recentSaved = dictionaryItems.slice(0, 6);

  return (
    <AppShell>
      <div className="space-y-4">

        {/* ── Row 1: Hero/Profile (72%) + Engine (28%) ─────────────────────── */}
        <div className="grid gap-4 lg:grid-cols-[72fr_28fr]">
          <div className="flex h-full flex-col gap-4">
            {/* Hero */}
            <section
              className="relative min-h-[220px] flex-1 overflow-hidden rounded-xl border border-[#D5D9EF] shadow-material"
              style={{ background: "#F1F3FA" }}
            >
              {/* Hero PNG — right side, contained */}
              <div className="pointer-events-none absolute inset-y-0 right-0 hidden lg:block" style={{ width: "46%" }}>
                <Image src="/gemmalens_hero.webp" alt="" fill className="object-cover object-center opacity-90" priority />
              </div>

              {/* Gradient: white left → transparent center */}
              <div
                className="pointer-events-none absolute inset-0 z-10 hidden lg:block"
                style={{ background: "linear-gradient(90deg, #ffffff 28%, rgba(255,255,255,0.92) 42%, rgba(241,243,250,0) 58%)" }}
              />

              {/* Right-edge subtle darkening */}
              <div
                className="pointer-events-none absolute inset-0 z-10 hidden lg:block"
                style={{ background: "linear-gradient(90deg, transparent 78%, rgba(208,214,236,0.28) 100%)" }}
              />

              {/* Content */}
              <div className="relative z-20 flex h-full min-h-[220px] items-center px-10 py-7">
                <div className="min-w-0 max-w-[440px]">
                  <h1 className="text-[30px] font-bold leading-[1.15] tracking-tight text-ink">
                    Read difficult knowledge.<br />
                    <span className="text-accent">Build lasting language.</span>
                  </h1>
                  <p className="mt-3 max-w-[380px] text-[15px] leading-relaxed text-secondary">
                    A local-first Gemma 4 reading coach for papers, technical documents, and subtitles.
                  </p>
                  <div className="mt-6 flex flex-wrap gap-3">
                    <PrimaryAction href="/documents" label="Analyze a document" icon={<FileText size={15} />} />
                    <SecondaryAction href="/video" label="Study a video" icon={<Video size={15} />} />
                    <SecondaryAction href="/settings" label="Set learning profile" icon={<ArrowRight size={15} />} />
                  </div>
                </div>
              </div>
            </section>
          </div>

          {/* Gemma Engine panel */}
          <ModelStatusCard status={modelStatus} compact />
        </div>

        {/* ── Row 2: Continue reading (55%) + Metrics 2×2 (45%) ────────────── */}
        <div className="grid gap-4 lg:grid-cols-[55fr_45fr]">

          {/* Continue reading */}
          <section className="rounded-xl border border-line bg-panel shadow-material">
            <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-3.5">
              <h2 className="text-[15px] font-semibold text-ink">Continue reading</h2>
              <Link href="/documents" className="inline-flex items-center gap-1 text-[13px] font-semibold text-accent hover:underline">
                All papers <ArrowRight size={13} />
              </Link>
            </div>

            {topDoc ? (
              <>
                <div className="flex items-start gap-5 p-5">
                  {/* PDF thumbnail */}
                  <div className="relative flex h-[80px] w-[60px] shrink-0 flex-col overflow-hidden rounded-lg border border-[#DBEAFE] bg-white shadow-sm">
                    <div className="flex-1 space-y-1 p-2 pt-2.5">
                      <div className="h-[5px] w-full rounded-full bg-[#E5E7EB]" />
                      <div className="h-[5px] w-4/5 rounded-full bg-[#E5E7EB]" />
                      <div className="h-[5px] w-full rounded-full bg-[#E5E7EB]" />
                      <div className="h-[5px] w-3/5 rounded-full bg-[#E5E7EB]" />
                      <div className="h-[5px] w-4/5 rounded-full bg-[#EFF6FF]" />
                    </div>
                    <div className="border-t border-[#DBEAFE] bg-accent-soft px-1.5 py-1 text-center">
                      <span className="text-[7px] font-bold uppercase tracking-wide text-accent">PDF</span>
                    </div>
                  </div>

                  {/* Info */}
                  <div className="min-w-0 flex-1">
                    <p className="text-[15px] font-semibold leading-snug text-ink">{topDoc.title}</p>
                    <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11px] text-secondary">
                      {topDocTotal > 1 ? (
                        <>
                          <span>Section {topDocAnalyzed} of {topDocTotal}</span>
                          <span className="text-line">·</span>
                        </>
                      ) : null}
                      <span className={topDocTerms.length > 0 ? "font-semibold text-accent" : ""}>
                        {topDocTerms.length} term{topDocTerms.length !== 1 ? "s" : ""} saved
                      </span>
                      {topDoc.source_type === "pdf" ? (
                        <>
                          <span className="text-line">·</span>
                          <span className="rounded-full bg-accent-soft px-1.5 py-px font-semibold text-accent">PDF</span>
                        </>
                      ) : null}
                    </div>
                    {topDocTotal > 1 ? (
                      <div className="mt-2.5 h-1.5 max-w-[260px] overflow-hidden rounded-full bg-[#E5E7EB]">
                        <div
                          className="h-full rounded-full bg-accent transition-all"
                          style={{ width: `${Math.max(topDocProgress, topDocAnalyzed > 0 ? 4 : 0)}%` }}
                        />
                      </div>
                    ) : null}
                    <p className="mt-2 line-clamp-2 text-[13px] leading-[1.6] text-secondary">
                      {cleanDocumentPreview(topDoc)}
                    </p>
                  </div>

                  {/* Stacked CTAs — right */}
                  <div className="hidden shrink-0 flex-col gap-2 pt-0.5 lg:flex">
                    <PrimaryAction href={`/analysis/${topDoc.id}`} label="Continue lesson" icon={<BookOpen size={14} />} />
                    <SecondaryAction href={`/analysis/${topDoc.id}`} label="Open paper map" icon={<Map size={14} />} />
                  </div>
                </div>

                {/* Mobile CTAs */}
                <div className="flex gap-2 border-t border-line px-5 pb-4 pt-3 lg:hidden">
                  <PrimaryAction href={`/analysis/${topDoc.id}`} label="Continue lesson" icon={<BookOpen size={13} />} />
                  <SecondaryAction href={`/analysis/${topDoc.id}`} label="Open paper map" icon={<Map size={13} />} />
                </div>

                {recentDocs.length > 1 ? (
                  <div className="divide-y divide-line border-t border-line px-5">
                    {recentDocs.slice(1, 4).map((doc) => (
                      <Link
                        key={doc.id}
                        href={`/analysis/${doc.id}`}
                        className="flex items-center justify-between gap-3 py-2.5 text-[13px] transition-opacity hover:opacity-70"
                      >
                        <span className="min-w-0 truncate font-medium text-ink">{doc.title}</span>
                        <ProgressChip document={doc} />
                      </Link>
                    ))}
                  </div>
                ) : null}
              </>
            ) : (
              <div className="p-5"><EmptyDocs /></div>
            )}
          </section>

          {/* Metrics 2×2 */}
          <div className="grid grid-cols-2 grid-rows-2 gap-4 h-full">
            <MetricCard value={totalAnalyzed}          label="Sections"  sublabel="Analyzed" accent />
            <MetricCard value={dictionaryItems.length} label="Terms"     sublabel="Saved" />
            <MetricCard value={phraseItems.length}     label="Phrases"   sublabel="Found" />
            <MetricCard value={reviewTotal}            label="Review Items" sublabel="Ready" />
          </div>
        </div>

        {/* ── Row 3: Review queue · Recent saved · Today's focus ────────────── */}
        <div className="grid gap-4 sm:grid-cols-3">

          {/* Review queue */}
          <section className="flex flex-col rounded-xl border border-line bg-panel p-5 shadow-material">
            <div className="flex items-center justify-between gap-2">
              <p className="text-[13px] font-bold uppercase tracking-[0.1em] text-muted">Review queue</p>
              {reviewTotal > 0 && (
                <div className="flex items-center gap-3 text-[12px] font-semibold text-secondary">
                  <span className="flex items-center gap-1.5">
                    <span className="rounded bg-[#F1F5F9] px-1.5 py-0.5 text-[10px] font-bold text-[#374151]">T</span>
                    term
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="rounded bg-accent-soft px-1.5 py-0.5 text-[10px] font-bold text-accent">P</span>
                    phrase
                  </span>
                </div>
              )}
            </div>
            {reviewTotal > 0 ? (
              <>
                <p className="mt-1.5 text-[14px] font-semibold text-ink">
                  {reviewTotal} item{reviewTotal !== 1 ? "s" : ""} ready
                </p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {termItems.slice(0, 5).map((item) => (
                    <span key={item.id} className="inline-flex max-w-[150px] items-center gap-1.5 rounded-full border border-[#E5E7EB] bg-white px-2.5 py-1 text-[11px] font-medium text-ink">
                      <span className="shrink-0 rounded bg-[#F1F5F9] px-1 py-px text-[7px] font-bold text-[#374151]">T</span>
                      <span className="truncate">{item.text}</span>
                    </span>
                  ))}
                  {phraseItems.slice(0, Math.max(0, 5 - Math.min(termItems.length, 5))).map((item) => (
                    <span key={item.id} className="inline-flex max-w-[150px] items-center gap-1.5 rounded-full border border-[#DBEAFE] bg-accent-soft px-2.5 py-1 text-[11px] font-medium text-accent">
                      <span className="shrink-0 rounded bg-accent/10 px-1 py-px text-[7px] font-bold">P</span>
                      <span className="truncate">{item.text}</span>
                    </span>
                  ))}
                </div>
                <div className="mt-auto pt-4 flex justify-end">
                  <Link href="/quiz" className="inline-flex items-center gap-1 text-[13px] font-semibold text-accent hover:underline">
                    Start review <ArrowRight size={13} />
                  </Link>
                </div>
              </>
            ) : (
              <>
                <p className="mt-2 text-[14px] text-secondary">Nothing to review yet.</p>
                <p className="mt-1 text-[12px] text-muted">Analyze a document to start saving terms.</p>
                <Link href="/documents" className="mt-3 inline-flex items-center gap-1 text-[13px] font-semibold text-accent hover:underline">
                  Upload a paper <ArrowRight size={13} />
                </Link>
              </>
            )}
          </section>

          {/* Recent saved */}
          <section className="rounded-xl border border-line bg-panel p-5 shadow-material">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-[13px] font-bold uppercase tracking-[0.1em] text-muted">Recent saved</p>
              <Link href="/dictionary" className="text-[13px] font-semibold text-accent hover:underline">View library →</Link>
            </div>
            {recentSaved.length > 0 ? (
              <div className="space-y-3">
                {recentSaved.slice(0, 3).map((item) => (
                  <div key={item.id} className="flex items-start gap-2.5">
                    <span className={`mt-0.5 shrink-0 rounded px-1.5 py-px text-[9px] font-bold uppercase tracking-wide ${
                      item.item_type === "phrase" ? "bg-accent-soft text-accent"
                      : item.item_type === "concept" ? "bg-purple-50 text-purple-600"
                      : "bg-[#F1F5F9] text-[#374151]"
                    }`}>
                      {item.item_type === "sentence" ? "sent" : item.item_type}
                    </span>
                    <div className="min-w-0">
                      <p className="text-[13px] font-semibold leading-snug text-ink">{item.text}</p>
                      {item.meaning ? <p className="mt-0.5 line-clamp-1 text-[11px] text-secondary">{item.meaning}</p> : null}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[13px] text-muted">Nothing saved yet.</p>
            )}
          </section>

          {/* Today's focus */}
          <TodaysFocus
            topDocTitle={topDoc?.title ?? null}
            topDocProgress={topDocProgress}
            totalAnalyzed={totalAnalyzed}
            topDocId={topDoc?.id ?? null}
          />
        </div>

      </div>
    </AppShell>
  );
}

// ── Today's focus ─────────────────────────────────────────────────────────────

function TodaysFocus({
  topDocTitle, topDocProgress, totalAnalyzed, topDocId,
}: {
  topDocTitle: string | null;
  topDocProgress: number;
  totalAnalyzed: number;
  topDocId: string | null;
}) {
  const pct = topDocProgress > 0 ? topDocProgress : totalAnalyzed > 0 ? 12 : 0;
  const message =
    pct >= 100 ? "Source-grounded map complete."
    : pct > 50  ? "The paper map is taking shape."
    : totalAnalyzed > 0 ? "Keep reading with source-grounded support."
    : "Start with one real paper or transcript.";
  const nextAction =
    pct >= 100 ? "Use saved concepts and phrases for review."
    : topDocId ? "Continue where you left off, then save what repeats."
    : "Upload a PDF or subtitle transcript to build a learning workspace.";

  return (
    <section className="rounded-xl border border-line bg-panel p-5 shadow-material">
      <p className="text-[13px] font-bold uppercase tracking-[0.1em] text-muted">Today&apos;s focus</p>
      {topDocTitle ? (
        <p className="mt-2 line-clamp-1 text-[14px] font-semibold text-ink">{topDocTitle}</p>
      ) : null}
      <div className="mt-3">
        <div className="mb-1.5 flex items-center justify-between text-[11px] text-secondary">
          <span>{topDocTitle ? "Paper progress" : "Get started"}</span>
          <span className="font-semibold text-ink">{pct}%</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#E5E7EB]">
          <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${pct}%` }} />
        </div>
      </div>
      <p className="mt-2.5 text-[12px] leading-[1.55] text-secondary">{message}</p>
      <p className="mt-1 text-[12px] font-medium text-ink">{nextAction}</p>
      {topDocId ? (
        <Link href={`/analysis/${topDocId}`} className="mt-3 inline-flex items-center gap-1 text-[13px] font-semibold text-accent hover:underline">
          Continue reading <ArrowRight size={13} />
        </Link>
      ) : null}
    </section>
  );
}

// ── Components ────────────────────────────────────────────────────────────────

function MetricCard({ value, label, sublabel, accent = false }: {
  value: number;
  label: string;
  sublabel: string;
  accent?: boolean;
}) {
  return (
    <div className="flex flex-col justify-center rounded-xl border border-line bg-panel px-5 py-5 shadow-material">
      <p className={`text-[34px] font-bold tabular-nums leading-none ${accent ? "text-accent" : "text-ink"}`}>
        {value}
      </p>
      <div className="mt-2.5">
        <p className="text-[15px] font-bold text-ink">{label}</p>
        <p className="text-[13px] text-secondary">{sublabel}</p>
      </div>
    </div>
  );
}

function ProgressChip({ document }: { document: DocumentListItem }) {
  const label = documentProgressText(document);
  const analyzed = document.analyzed_sections ?? 0;
  const total = document.total_sections ?? 0;
  const tone =
    label === "Complete" || label === "Ready" ? "bg-green-50 text-green-700"
    : analyzed > 0 && total > 1 ? "bg-amber-50 text-amber-700"
    : "bg-surface text-muted border border-line";
  return (
    <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${tone}`}>
      {label === "Not ready" ? "New" : label}
    </span>
  );
}

function EmptyDocs() {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg bg-surface px-4 py-8 text-center">
      <FileText size={22} className="text-muted" />
      <p className="text-sm font-medium text-secondary">No papers yet</p>
      <p className="max-w-[240px] text-xs text-muted">Add a PDF, paper excerpt, or transcript to build a source-grounded learning workspace.</p>
      <Link href="/documents" className="mt-2 inline-flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-white">
        <FileText size={12} /> Add a document
      </Link>
    </div>
  );
}

function PrimaryAction({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-[13px] font-semibold text-white transition-all duration-150 hover:-translate-y-px hover:bg-accent-hover hover:shadow-[0_6px_16px_rgba(37,99,235,0.20)] active:translate-y-0"
    >
      {icon}
      {label}
    </Link>
  );
}

function SecondaryAction({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-2 rounded-md border border-line bg-white px-4 py-2 text-[13px] font-semibold text-ink transition-colors hover:border-[#CBD5E1] hover:bg-[#F8FAFC]"
    >
      {icon}
      {label}
    </Link>
  );
}
