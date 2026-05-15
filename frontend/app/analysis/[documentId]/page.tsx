import { AnalysisResultView } from "@/components/analysis/AnalysisResultView";
import { AppShell } from "@/components/layout/AppShell";

export default async function AnalysisPage({ params }: { params: Promise<{ documentId: string }> }) {
  const { documentId } = await params;
  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Analysis result</h1>
        <p className="mt-2 max-w-3xl text-sm text-neutral-600">
          Read the original source beside a language-learning guide built from extracted text, concepts, expressions, and sentence structures.
        </p>
      </div>
      <AnalysisResultView documentId={documentId} />
    </AppShell>
  );
}
