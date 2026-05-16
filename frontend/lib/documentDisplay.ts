import type { DocumentListItem } from "./types";

export function displayableDocuments(documents: DocumentListItem[]) {
  const bestByKey = new Map<string, DocumentListItem>();
  for (const document of documents) {
    const key = `${document.source_type}:${document.title.trim().toLowerCase()}`;
    const current = bestByKey.get(key);
    if (!current || documentDisplayScore(document) > documentDisplayScore(current)) {
      bestByKey.set(key, document);
    }
  }
  return Array.from(bestByKey.values()).sort((a, b) => Number(new Date(b.created_at)) - Number(new Date(a.created_at)));
}

export function cleanDocumentPreview(document: DocumentListItem) {
  const total = document.total_sections ?? 0;
  const analyzed = document.analyzed_sections ?? 0;
  if (total > 1 && analyzed >= total) {
    return `Complete paper guide ready: ${total} sections analyzed with concepts, terms, expressions, and review flow.`;
  }
  if (total > 1 && analyzed > 0) {
    return `In progress: ${analyzed} of ${total} sections studied. Continue from the next unstudied section.`;
  }

  const cleaned = document.preview
    .replace(/\[\[GEMMALENS_PDF_PAGE:\d+]]/g, " ")
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, " ")
    .replace(/\{[^}]{8,120}\}/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  if (cleaned.length < 40) {
    return "Source text extracted. Open the document to start a section-level reading guide.";
  }
  return cleaned;
}

export function documentProgressText(document: DocumentListItem) {
  const total = document.total_sections ?? 0;
  const analyzed = document.analyzed_sections ?? 0;
  if (total <= 1) return analyzed > 0 ? "Ready" : "Not studied";
  if (analyzed >= total) return "Complete";
  if (analyzed > 0) return `${analyzed}/${total} studied`;
  return "Not studied";
}

export function isVideoSource(sourceType: string) {
  return sourceType === "transcript" || sourceType === "video_segment";
}

function documentDisplayScore(document: DocumentListItem) {
  const total = Math.max(document.total_sections ?? 0, 1);
  const analyzed = document.analyzed_sections ?? 0;
  const completion = analyzed >= total && total > 1 ? 1000 : Math.round((analyzed / total) * 100);
  return completion * 1_000_000 + Number(new Date(document.created_at));
}
