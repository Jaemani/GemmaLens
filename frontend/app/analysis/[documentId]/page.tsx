import { AnalysisResultView } from "@/components/analysis/AnalysisResultView";
import { AppShell } from "@/components/layout/AppShell";

export default async function AnalysisPage({ params }: { params: Promise<{ documentId: string }> }) {
  const { documentId } = await params;
  return (
    <AppShell>
      <AnalysisResultView documentId={documentId} />
    </AppShell>
  );
}
