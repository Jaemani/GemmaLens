import { AnalysisResultView } from "@/components/analysis/AnalysisResultView";
import { AppShell } from "@/components/layout/AppShell";

export default async function AnalysisPage({ params }: { params: Promise<{ documentId: string }> }) {
  const { documentId } = await params;
  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Analysis result</h1>
        <p className="mt-2 max-w-3xl text-sm text-neutral-600">
          Learning guide generated from extracted source text. For PDFs, the current view is not a rendered page viewer yet.
        </p>
      </div>
      <AnalysisResultView documentId={documentId} />
    </AppShell>
  );
}
