import type {
  AnalysisResult,
  DictionaryItem,
  DocumentListItem,
  DocumentRead,
  ModelConfigUpdate,
  ModelPreset,
  ModelStatus,
  TranscriptResponse,
  UserProfile
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 30000;
const ANALYSIS_TIMEOUT_MS = 300000;

type ApiRequestInit = RequestInit & {
  timeoutMs?: number;
};

function timeoutSignal(ms = REQUEST_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeout = globalThis.setTimeout(() => controller.abort(), ms);
  return { signal: controller.signal, clear: () => globalThis.clearTimeout(timeout) };
}

async function request<T>(path: string, init?: ApiRequestInit): Promise<T> {
  const { timeoutMs, ...fetchInit } = init ?? {};
  const timeout = timeoutSignal(timeoutMs ?? REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...fetchInit,
      signal: fetchInit.signal ?? timeout.signal,
      headers: {
        "Content-Type": "application/json",
        ...(fetchInit.headers ?? {})
      },
      cache: "no-store"
    });
    if (!response.ok) {
      throw new Error(await responseErrorMessage(response));
    }
    return response.json() as Promise<T>;
  } catch (err) {
    throw normalizeRequestError(err);
  } finally {
    timeout.clear();
  }
}

async function responseErrorMessage(response: Response) {
  const text = await response.text();
  try {
    const parsed = JSON.parse(text) as { detail?: unknown };
    if (typeof parsed.detail === "string") return parsed.detail;
  } catch {
    // Fall through to raw response text.
  }
  return text || `Request failed with ${response.status}`;
}

function normalizeRequestError(err: unknown) {
  if (err instanceof DOMException && err.name === "AbortError") {
    return new Error("Request timed out. Check that the local backend is running and reachable from this browser.");
  }
  if (err instanceof TypeError) {
    return new Error("Could not reach the backend. Check the backend URL, CORS, and whether this browser can access the local server.");
  }
  return err instanceof Error ? err : new Error("Request failed.");
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
    const timeout = timeoutSignal();
    try {
      const response = await fetch(`${API_BASE}/documents/upload`, {
        method: "POST",
        body: formData,
        signal: timeout.signal,
        cache: "no-store"
      });
      if (!response.ok) throw new Error(await responseErrorMessage(response));
      return response.json() as Promise<DocumentRead>;
    } catch (err) {
      throw normalizeRequestError(err);
    } finally {
      timeout.clear();
    }
  },
  analyzeDocument: (documentId: string) =>
    request<AnalysisResult>(`/documents/${documentId}/analyze`, { method: "POST", timeoutMs: ANALYSIS_TIMEOUT_MS }),
  getAnalysis: (documentId: string) => request<AnalysisResult>(`/documents/${documentId}/analysis`),
  listDictionary: () => request<DictionaryItem[]>("/dictionary/items"),
  markDictionaryViewed: (itemId: string) =>
    request<DictionaryItem>(`/dictionary/items/${itemId}/view`, { method: "POST" }),
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
  },
  getProfile: () => request<UserProfile>("/profile"),
  updateProfile: (payload: Partial<Omit<UserProfile, "id" | "created_at">>) =>
    request<UserProfile>("/profile", { method: "PATCH", body: JSON.stringify(payload) }),
  parseTranscript: (payload: { content: string; source_name: string }) =>
    request<TranscriptResponse>("/video/transcripts/parse", { method: "POST", body: JSON.stringify(payload) }),
  fetchYouTubeTranscript: (payload: { url: string; languages?: string[] }) =>
    request<TranscriptResponse>("/video/transcripts/youtube", { method: "POST", body: JSON.stringify(payload) })
};
