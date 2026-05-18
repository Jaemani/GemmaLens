import { BookOpen, BookmarkPlus, FileText, Languages, Map, PanelsTopLeft, PlaySquare, ScanText } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";

const workflow = [
  {
    icon: FileText,
    title: "Upload or paste",
    detail: "PDF, DOCX, markdown, text, or transcript becomes a source document. PDFs keep the original file when available."
  },
  {
    icon: PanelsTopLeft,
    title: "Read beside the source",
    detail: "For PDFs, the original page stays visible while the learning panel explains the current section."
  },
  {
    icon: ScanText,
    title: "Read while it prepares",
    detail: "The first page appears immediately. By default, GemmaLens prepares every page section in the background to reduce waiting."
  },
  {
    icon: Map,
    title: "Build the paper map",
    detail: "As sections finish, GemmaLens builds an outline of argument flow, concepts, terms, and expressions."
  },
  {
    icon: BookmarkPlus,
    title: "Save what matters",
    detail: "Save concepts, terms, expressions, and hard sentence patterns separately so review can stay targeted."
  }
];

const learningObjects = [
  {
    title: "Key ideas",
    detail: "Ideas needed to follow the paper's argument, such as the method, objective, ablation, or benchmark setup."
  },
  {
    title: "Terms",
    detail: "Source-grounded vocabulary and domain terms worth saving only if they are unfamiliar or repeated."
  },
  {
    title: "Reusable expressions",
    detail: "Academic moves such as contrast, limitation, method setup, result claims, and conclusion language."
  },
  {
    title: "Sentence patterns",
    detail: "Dense structures are simplified and explained so the learner can read similar sentences later."
  }
];

const expectations = [
  "PDF pages remain the visual source. Extracted text powers the lesson, so complex equations or unusual columns may need source-side checking.",
  "The paper map is built from section lessons instead of one large summary, which keeps local inference responsive.",
  "Translation is for quick sentence help. Documents and Video are the main learning workspaces.",
  "Video learning works best with verified subtitles, either local SRT/VTT files or a stable public transcript."
];

const runtimes = [
  {
    title: "ThinkPad / small local model",
    detail: "Runs the same section pipeline with lower memory pressure; background preparation hides per-section delay."
  },
  {
    title: "Mac M1 Max",
    detail: "Fast local inference can prepare many sections while the learner reads the visible page."
  },
  {
    title: "Mobile / edge demo",
    detail: "The product story still works on constrained devices because work is split into small page-section jobs."
  }
];

const levels = [
  { label: "B1", detail: "Needs help with main ideas, academic phrases, and dense grammar." },
  { label: "B2", detail: "Can read general academic text with support for domain words and long sentences." },
  { label: "C1", detail: "Can read research writing but benefits from structure, nuance, and reusable expression notes." },
  { label: "C2", detail: "Focuses on precision, rhetoric, field-specific phrasing, and paper-level argument flow." },
  { label: "Domain-heavy", detail: "Difficulty comes mainly from specialist concepts rather than grammar." }
];

const videoWorkflow = [
  {
    title: "Local subtitle study",
    detail: "Open a local video and attach English subtitles. The timeline follows playback and supports line-level study."
  },
  {
    title: "Live cues",
    detail: "While watching, GemmaLens surfaces lightweight vocabulary and phrases from the current subtitle window."
  },
  {
    title: "Scene lessons",
    detail: "Analyze a short scene for concepts, spoken expressions, and source-grounded review items."
  },
  {
    title: "Recap watched part",
    detail: "Use deeper recap after watching a larger segment, then save useful terms and expressions for review."
  }
];

export default function GuidePage() {
  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-3xl font-semibold text-ink">Guide</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-700">
          GemmaLens turns academic papers, technical documents, and subtitles into source-grounded language lessons. The goal is not to replace reading with translation; it is to help you read the next source with less support.
        </p>
      </div>

      <div className="space-y-6">
        <section className="rounded-lg border border-line bg-panel p-6 shadow-material">
          <div className="flex items-start gap-3">
            <div className="rounded-md bg-blue-50 p-2 text-accent">
              <BookOpen size={18} />
            </div>
            <div>
              <h2 className="text-xl font-semibold">Paper reading</h2>
              <p className="mt-1 text-sm leading-6 text-neutral-600">
                Start with the original source. GemmaLens opens the first prepared lesson quickly, then continues preparing the rest while you read.
              </p>
            </div>
          </div>
          <div className="mt-5 grid gap-3 lg:grid-cols-5">
            {workflow.map((item, index) => {
              const Icon = item.icon;
              return (
                <div key={item.title} className="rounded-md border border-line bg-surface p-4">
                  <div className="flex items-center justify-between gap-3">
                    <Icon size={18} className="text-accent" />
                    <span className="text-xs font-semibold text-neutral-500">Step {index + 1}</span>
                  </div>
                  <p className="mt-3 font-semibold text-ink">{item.title}</p>
                  <p className="mt-2 text-xs leading-5 text-neutral-600">{item.detail}</p>
                </div>
              );
            })}
          </div>
        </section>

        <section className="rounded-lg border border-line bg-panel p-6 shadow-material">
          <h2 className="text-xl font-semibold">Local-first preparation</h2>
          <p className="mt-2 text-sm leading-6 text-neutral-600">
            GemmaLens does not wait for a whole-paper pass before becoming useful. It breaks long sources into small jobs, which lets local Gemma models prepare useful lessons without sending your paper to a remote reading service.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {runtimes.map((item) => (
              <GuideItem key={item.title} title={item.title} detail={item.detail} accent />
            ))}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="rounded-lg border border-line bg-panel p-6 shadow-material">
            <h2 className="text-xl font-semibold">Learning objects</h2>
            <p className="mt-2 text-sm leading-6 text-neutral-600">
              GemmaLens separates different kinds of help so the lesson does not become a wall of generated text.
            </p>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {learningObjects.map((item) => (
                <GuideItem key={item.title} title={item.title} detail={item.detail} />
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-line bg-panel p-6 shadow-material">
            <h2 className="text-xl font-semibold">Translation</h2>
            <div className="mt-4 rounded-md bg-surface p-4">
              <Languages size={18} className="text-accent" />
              <p className="mt-3 text-sm leading-6 text-neutral-700">
                Use Translate for short passages. Use Documents or Video for real study, because those workspaces preserve source context, repeated terms, and review history.
              </p>
            </div>
          </div>
        </section>

        <section className="rounded-lg border border-line bg-panel p-6 shadow-material">
          <div className="flex items-start gap-3">
            <div className="rounded-md bg-blue-50 p-2 text-accent">
              <PlaySquare size={18} />
            </div>
            <div>
              <h2 className="text-xl font-semibold">Video study</h2>
              <p className="mt-2 text-sm leading-6 text-neutral-600">
                Video mode treats subtitles as timestamped reading material. It is strongest when you have a reliable English subtitle file or stable public transcript.
              </p>
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {videoWorkflow.map((item) => (
              <GuideItem key={item.title} title={item.title} detail={item.detail} accent />
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-line bg-panel p-6 shadow-material">
          <h2 className="text-xl font-semibold">Reading levels</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {levels.map((level) => (
              <GuideItem key={level.label} title={level.label} detail={level.detail} accent />
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-line bg-panel p-6 shadow-material">
          <h2 className="text-xl font-semibold">Notes</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {expectations.map((item) => (
              <div key={item} className="rounded-md border border-line bg-surface p-4 text-sm leading-6 text-neutral-700">
                {item}
              </div>
            ))}
          </div>
        </section>

      </div>
    </AppShell>
  );
}

function GuideItem({ title, detail, accent = false }: { title: string; detail: string; accent?: boolean }) {
  return (
    <div className="rounded-md border border-line p-4">
      <p className={`font-semibold ${accent ? "text-accent" : "text-ink"}`}>{title}</p>
      <p className="mt-2 text-sm leading-6 text-neutral-700">{detail}</p>
    </div>
  );
}
