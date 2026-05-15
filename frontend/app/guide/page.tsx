import { AppShell } from "@/components/layout/AppShell";

const levels = [
  { label: "B1", detail: "Can follow main ideas but needs support for academic phrases and dense grammar." },
  { label: "B2", detail: "Can read general academic text with help for domain words and long sentences." },
  { label: "C1", detail: "Can read research-style writing but benefits from structure, nuance, and reusable expression notes." },
  { label: "C2", detail: "Near-native academic reading. Focus is precision, rhetoric, and field-specific phrasing." },
  { label: "Domain-heavy", detail: "Difficulty comes less from grammar and more from specialist vocabulary or concepts." }
];

const scores = [
  { label: "Lexical", detail: "Vocabulary load: rare terms, academic words, multi-word expressions, and field-specific meanings." },
  { label: "Syntax", detail: "Sentence structure load: clauses, passive constructions, embedded questions, references, and long noun phrases." },
  { label: "Domain", detail: "Background knowledge load: how much subject knowledge is needed before the language makes sense." }
];

export default function GuidePage() {
  return (
    <AppShell>
      <div className="mb-6">
        <p className="text-sm font-semibold uppercase text-accent">User guide</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">How PaperLens works</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-700">
          PaperLens turns academic or technical documents into language-learning material. It is a prototype, so details may change, but this page explains the current behavior and intended product direction.
        </p>
      </div>

      <div className="space-y-6">
        <section className="rounded-2xl border border-line bg-panel p-6 shadow-material">
          <h2 className="text-xl font-semibold">Current flow</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-5">
            {["Input", "Chunk", "Analyze", "Structure", "Save"].map((item, index) => (
              <div key={item} className="rounded-2xl bg-surface p-4">
                <p className="text-xs font-semibold text-accent">Step {index + 1}</p>
                <p className="mt-2 font-semibold">{item}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-line bg-panel p-6 shadow-material">
          <h2 className="text-xl font-semibold">Learning levels</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {levels.map((level) => (
              <div key={level.label} className="rounded-2xl border border-line p-4">
                <p className="font-semibold text-accent">{level.label}</p>
                <p className="mt-2 text-sm leading-6 text-neutral-700">{level.detail}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-line bg-panel p-6 shadow-material">
          <h2 className="text-xl font-semibold">Difficulty scores</h2>
          <p className="mt-2 text-sm text-neutral-700">Scores use a 0-10 scale. They are learning-priority signals, not official exam grades.</p>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {scores.map((score) => (
              <div key={score.label} className="rounded-2xl bg-surface p-4">
                <p className="font-semibold">{score.label}</p>
                <p className="mt-2 text-sm leading-6 text-neutral-700">{score.detail}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-line bg-panel p-6 shadow-material">
          <h2 className="text-xl font-semibold">Language direction</h2>
          <p className="mt-2 text-sm leading-6 text-neutral-700">
            The prototype began with Korean learners reading English papers, but the interface now supports searchable language selection for broad Gemma-family multilingual coverage.
          </p>
          <p className="mt-4 text-sm leading-6 text-neutral-700">
            The core stays model-driven: prompts can request explanations, translations, sentence decomposition, and study notes in the selected support language while analyzing the selected learning language. Actual quality must be tested per language pair.
          </p>
        </section>

        <section className="rounded-2xl border border-line bg-panel p-6 shadow-material">
          <h2 className="text-xl font-semibold">What is saved</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <GuideItem title="Terms" detail="Important vocabulary, domain terms, and multi-word technical expressions." />
            <GuideItem title="Phrases" detail="Academic expressions like claims, contrast, limitations, methods, and results." />
            <GuideItem title="Sentences" detail="Difficult structures with simplified versions and support-language explanations." />
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function GuideItem({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-line p-4">
      <p className="font-semibold">{title}</p>
      <p className="mt-2 text-sm leading-6 text-neutral-700">{detail}</p>
    </div>
  );
}
