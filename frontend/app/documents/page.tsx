import { DocumentInputPanel } from "@/components/document/DocumentInputPanel";
import { DocumentPreview } from "@/components/document/DocumentPreview";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import { demoModeEnabled } from "@/lib/demoMode";
import { demoDocuments } from "@/lib/demoData";
import type { DocumentListItem } from "@/lib/types";

export default async function DocumentsPage() {
  let documents: DocumentListItem[] = [];
  try {
    documents = await api.listDocuments();
  } catch {
    documents = demoModeEnabled ? demoDocuments : [];
  }
  const documentOnlyItems = documents.filter((document) => document.source_type !== "transcript" && document.source_type !== "video_segment");

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl">
        <div className="mb-5">
        <h1 className="text-2xl font-semibold">Document input</h1>
        <p className="mt-2 text-sm text-neutral-600">
          Upload a document or paste a focused excerpt, then generate structured learning objects.
        </p>
        </div>
        <div className="space-y-6">
          <DocumentInputPanel />
          {documentOnlyItems.length > 0 ? <DocumentPreview documents={documentOnlyItems} /> : null}
        </div>
      </div>
    </AppShell>
  );
}
