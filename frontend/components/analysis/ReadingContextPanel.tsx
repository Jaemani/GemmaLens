import type { AnalysisResult } from "@/lib/types";

export function ReadingContextPanel({ analysis }: { analysis: AnalysisResult }) {
  const sentences = Array.from(
    new Set([
      ...analysis.terms.map((term) => term.source_sentence),
      ...analysis.phrases.map((phrase) => phrase.source_sentence)
    ])
  ).filter(Boolean);

  return (
    <section className="rounded-lg border border-line bg-panel p-5 shadow-material">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Reading context</h2>
          <p className="mt-1 text-sm text-neutral-600">Highlighted learning objects in their source sentences.</p>
        </div>
        <span className="rounded-full bg-surface px-3 py-1 text-xs font-semibold text-neutral-600">B reader layout</span>
      </div>
      <div className="mt-4 space-y-4">
        {sentences.map((sentence) => (
          <p key={sentence} className="rounded-md bg-surface p-4 text-sm leading-7 text-neutral-800">
            {renderHighlightedSentence(sentence, analysis)}
          </p>
        ))}
      </div>
    </section>
  );
}

function renderHighlightedSentence(sentence: string, analysis: AnalysisResult) {
  const targets = [
    ...analysis.terms.map((term) => term.term),
    ...analysis.phrases.map((phrase) => phrase.phrase)
  ]
    .filter(Boolean)
    .sort((a, b) => b.length - a.length);

  const matches = targets
    .map((target) => ({ target, index: sentence.toLowerCase().indexOf(target.toLowerCase()) }))
    .filter((match) => match.index >= 0)
    .sort((a, b) => a.index - b.index);

  const parts: React.ReactNode[] = [];
  let cursor = 0;
  for (const match of matches) {
    if (match.index < cursor) continue;
    if (match.index > cursor) parts.push(sentence.slice(cursor, match.index));
    const text = sentence.slice(match.index, match.index + match.target.length);
    parts.push(
      <mark key={`${match.target}-${match.index}`} className="rounded bg-blue-100 px-1 py-0.5 text-ink">
        {text}
      </mark>
    );
    cursor = match.index + match.target.length;
  }
  if (cursor < sentence.length) parts.push(sentence.slice(cursor));
  return parts.length ? parts : sentence;
}
