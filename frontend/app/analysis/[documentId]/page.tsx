import { DomainOverviewCard } from "@/components/analysis/DomainOverviewCard";
import { LayeredSummaryPanel } from "@/components/analysis/LayeredSummaryPanel";
import { SentenceDecompositionCard } from "@/components/analysis/SentenceDecompositionCard";
import { TermTable } from "@/components/analysis/TermTable";
import { ErrorState } from "@/components/common/ErrorState";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";

export default async function AnalysisPage({ params }: { params: { documentId: string } }) {
  try {
    const analysis = await api.getAnalysis(params.documentId);
    return (
      <AppShell>
        <div className="mb-6">
          <h1 className="text-2xl font-semibold">Analysis result</h1>
          <p className="mt-2 text-sm text-neutral-600">Structured language learning output from this document.</p>
        </div>
        <div className="space-y-6">
          <DomainOverviewCard analysis={analysis} />
          <LayeredSummaryPanel analysis={analysis} />
          <TermTable analysis={analysis} />
          <section className="space-y-4">
            <h2 className="text-lg font-semibold">Sentence structures</h2>
            {analysis.sentences.map((sentence) => <SentenceDecompositionCard key={sentence.core_structure} sentence={sentence} />)}
          </section>
        </div>
      </AppShell>
    );
  } catch {
    return (
      <AppShell>
        <ErrorState message="Analysis not found. Create and analyze a document first." />
      </AppShell>
    );
  }
}
