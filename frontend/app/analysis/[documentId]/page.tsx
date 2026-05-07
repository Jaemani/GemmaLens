import { AnalysisResultView } from "@/components/analysis/AnalysisResultView";
import { AppShell } from "@/components/layout/AppShell";

export default async function AnalysisPage({ params }: { params: Promise<{ documentId: string }> }) {
  const { documentId } = await params;
  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Analysis result</h1>
        <p className="mt-2 text-sm text-neutral-600">Structured language learning output from this document.</p>
      </div>
      <AnalysisResultView documentId={documentId} />
    </AppShell>
  );
}
