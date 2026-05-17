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
    detail: "For PDFs, the left pane shows the original page while the right pane shows backend-cleaned text sections."
  },
  {
    icon: ScanText,
    title: "Read while it prepares",
    detail: "The first page appears immediately. By default, GemmaLens prepares every page section in the background to reduce waiting."
  },
  {
    icon: Map,
    title: "Build the paper map",
    detail: "The whole-paper guide grows from analyzed sections: argument flow, priority concepts, terms, and expressions."
  },
  {
    icon: BookmarkPlus,
    title: "Save what matters",
    detail: "Save concepts, terms, expressions, and hard sentence patterns separately so review can stay targeted."
  }
];

const learningObjects = [
  {
    title: "Concept anchors",
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
  "The PDF pane is the visual source. The section text is extracted text that the model can read, so equations and columns may be imperfect.",
  "A complete paper guide is built from section lessons, not from one huge summary call. This keeps latency low and lets fast local models prepare the rest while you read.",
  "Translation is a support tool for short passages. Full-paper learning should stay in the document reader.",
  "Video learning uses transcripts as timestamped text sections. YouTube caption endpoints can be rate-limited, so demos should use verified transcript fallback sources or pasted subtitles."
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

const demoPlan = [
  {
    title: "Show the source, not a chatbot",
    detail: "Open a PDF and keep the original page visible while section lessons prepare beside it."
  },
  {
    title: "Show fast local preparation",
    detail: "Start from the first page, then let background section preparation fill the paper map."
  },
  {
    title: "Show learner-level output",
    detail: "Switch between B1/B2/C1/C2 examples and point out how terms, expressions, and sentence guidance change."
  },
  {
    title: "Show video as learning source",
    detail: "Use one verified demo URL so the transcript path is stable, then analyze the current scene inline."
  }
];

export default function GuidePage() {
  return (
    <AppShell>
      <div className="mb-6">
        <p className="text-sm font-semibold uppercase text-accent">User guide</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">How to use GemmaLens</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-700">
          GemmaLens is for reading difficult academic material while learning the language around it. It should help you understand this paper and read the next one with less support.
        </p>
      </div>

      <div className="space-y-6">
        <section className="rounded-lg border border-line bg-panel p-6 shadow-material">
          <div className="flex items-start gap-3">
            <div className="rounded-md bg-blue-50 p-2 text-accent">
              <BookOpen size={18} />
            </div>
            <div>
              <h2 className="text-xl font-semibold">Paper reading workflow</h2>
              <p className="mt-1 text-sm leading-6 text-neutral-600">
                Start from the document page. For long PDFs, work section by section; the paper map becomes useful after several sections and complete after every section is ready.
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
          <h2 className="text-xl font-semibold">Why it feels fast</h2>
          <p className="mt-2 text-sm leading-6 text-neutral-600">
            GemmaLens does not wait for a whole-paper pass before becoming useful. It shows the first page, then analyzes page sections as small jobs. This is the demo advantage for Gemma 4 Good: the same product shape works from ThinkPad-class local models to Mac M1 Max and future mobile edge runtimes.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {runtimes.map((item) => (
              <GuideItem key={item.title} title={item.title} detail={item.detail} accent />
            ))}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="rounded-lg border border-line bg-panel p-6 shadow-material">
            <h2 className="text-xl font-semibold">What the analysis separates</h2>
            <p className="mt-2 text-sm leading-6 text-neutral-600">
              GemmaLens should not treat every interesting phrase as vocabulary. Concepts, terms, expressions, and sentence patterns have different jobs.
            </p>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {learningObjects.map((item) => (
                <GuideItem key={item.title} title={item.title} detail={item.detail} />
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-line bg-panel p-6 shadow-material">
            <h2 className="text-xl font-semibold">Where translation fits</h2>
            <div className="mt-4 rounded-md bg-surface p-4">
              <Languages size={18} className="text-accent" />
              <p className="mt-3 text-sm leading-6 text-neutral-700">
                Use Translate for quick sentence support. Use Documents for papers, because the document reader preserves source context, repeated terms, and the paper map.
              </p>
            </div>
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
          <h2 className="text-xl font-semibold">Current limits</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {expectations.map((item) => (
              <div key={item} className="rounded-md border border-line bg-surface p-4 text-sm leading-6 text-neutral-700">
                {item}
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-line bg-panel p-6 shadow-material">
          <div className="flex items-start gap-3">
            <div className="rounded-md bg-blue-50 p-2 text-accent">
              <PlaySquare size={18} />
            </div>
            <div>
              <h2 className="text-xl font-semibold">Gemma 4 Good demo strategy</h2>
              <p className="mt-2 text-sm leading-6 text-neutral-600">
                Position GemmaLens as a local-first learning harness: it converts real academic sources into durable reading skills, not just summaries. The demo should use verified PDF and video sources so the story is about learning quality and local speed, not network availability.
              </p>
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {demoPlan.map((item) => (
              <GuideItem key={item.title} title={item.title} detail={item.detail} accent />
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
