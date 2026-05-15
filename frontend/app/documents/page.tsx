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

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Document input</h1>
        <p className="mt-2 text-sm text-neutral-600">
          Upload a document or paste a focused excerpt, then generate structured learning objects.
        </p>
      </div>
      <div className="space-y-6">
        <DocumentInputPanel />
        {documents.length > 0 ? <DocumentPreview documents={documents} /> : null}
      </div>
    </AppShell>
  );
}
