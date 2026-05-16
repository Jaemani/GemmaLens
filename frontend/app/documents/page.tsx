import { DocumentInputPanel } from "@/components/document/DocumentInputPanel";
import { DocumentPreview } from "@/components/document/DocumentPreview";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import { demoModeEnabled } from "@/lib/demoMode";
import { demoDocuments } from "@/lib/demoData";
import { displayableDocuments, isVideoSource } from "@/lib/documentDisplay";
import type { DocumentListItem } from "@/lib/types";

export default async function DocumentsPage() {
  let documents: DocumentListItem[] = [];
  try {
    documents = await api.listDocuments();
  } catch {
    documents = demoModeEnabled ? demoDocuments : [];
  }
  const documentOnlyItems = displayableDocuments(documents.filter((document) => !isVideoSource(document.source_type)));

  return (
    <AppShell>
      <div className="w-full">
        <div className="mb-5">
          <h1 className="text-2xl font-semibold">Document input</h1>
          <p className="mt-2 max-w-3xl text-sm text-neutral-600">
            Upload a document or paste a focused excerpt, then generate structured learning objects. Original PDF rendering is a separate viewer step; current analysis uses extracted text.
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
