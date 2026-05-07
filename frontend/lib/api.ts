import type { AnalysisResult, DictionaryItem, DocumentListItem, DocumentRead, ModelConfigUpdate, ModelPreset, ModelStatus } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

export const api = {
  getModelStatus: () => request<ModelStatus>("/models/status"),
  listModelPresets: () => request<ModelPreset[]>("/models/presets"),
  updateModelConfig: (payload: ModelConfigUpdate) =>
    request<ModelStatus>("/models/config", { method: "POST", body: JSON.stringify(payload) }),
  listDocuments: () => request<DocumentListItem[]>("/documents"),
  createDocument: (payload: { title: string; content: string; source_type: string }) =>
    request<DocumentRead>("/documents", { method: "POST", body: JSON.stringify(payload) }),
  uploadDocument: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${API_BASE}/documents/upload`, {
      method: "POST",
      body: formData,
      cache: "no-store"
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json() as Promise<DocumentRead>;
  },
  analyzeDocument: (documentId: string) =>
    request<AnalysisResult>(`/documents/${documentId}/analyze`, { method: "POST" }),
  getAnalysis: (documentId: string) => request<AnalysisResult>(`/documents/${documentId}/analysis`),
  listDictionary: () => request<DictionaryItem[]>("/dictionary/items"),
  saveDictionaryItem: (payload: {
    item_type: "term" | "phrase" | "sentence";
    text: string;
    meaning?: string;
    source_sentence?: string;
    document_id?: string;
  }) => request<DictionaryItem>("/dictionary/items", { method: "POST", body: JSON.stringify(payload) }),
  deleteDictionaryItem: async (itemId: string) => {
    const response = await fetch(`${API_BASE}/dictionary/items/${itemId}`, { method: "DELETE" });
    if (!response.ok) throw new Error(await response.text());
  }
};
