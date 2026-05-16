import { AnalysisResultView } from "@/components/analysis/AnalysisResultView";
import { AppShell } from "@/components/layout/AppShell";

export default async function AnalysisPage({ params }: { params: Promise<{ documentId: string }> }) {
  const { documentId } = await params;
  return (
    <AppShell>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Language learning workspace</h1>
          <p className="mt-1 max-w-3xl text-sm text-neutral-600">
            Read the source, transcript, or section guide while building durable concepts, terms, expressions, and sentence patterns.
          </p>
        </div>
      </div>
      <AnalysisResultView documentId={documentId} />
    </AppShell>
  );
}
