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
const PROFILE_TIMEOUT_MS = 8000;
const UPLOAD_TIMEOUT_MS = 300000;
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
    const response = await fetch(`${apiBase()}${path}`, {
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
    throw normalizeRequestError(err, timeoutMs ?? REQUEST_TIMEOUT_MS);
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

function normalizeRequestError(err: unknown, timeoutMs = REQUEST_TIMEOUT_MS, phase = "request") {
  if (err instanceof DOMException && err.name === "AbortError") {
    const seconds = Math.round(timeoutMs / 1000);
    return new Error(`${phase} timed out after ${seconds}s. The backend may still be busy; wait or try a smaller text slice first.`);
  }
  if (err instanceof TypeError) {
    return new Error("Could not reach the backend. Check the backend URL, CORS, and whether this browser can access the local server.");
  }
  return err instanceof Error ? err : new Error("Request failed.");
}

function apiBase() {
  if (typeof window === "undefined") return API_BASE;
  const { protocol, hostname } = window.location;
  if (isLocalNetworkHost(hostname)) return `${protocol}//${hostname}:8012`;
  return API_BASE;
}

function isLocalNetworkHost(hostname: string) {
  if (hostname === "localhost" || hostname === "127.0.0.1") return true;
  if (hostname.startsWith("192.168.") || hostname.startsWith("10.") || hostname.startsWith("100.")) return true;
  const match = hostname.match(/^172\.(\d+)\./);
  return match ? Number(match[1]) >= 16 && Number(match[1]) <= 31 : false;
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
    const timeout = timeoutSignal(UPLOAD_TIMEOUT_MS);
    try {
      const response = await fetch(`${apiBase()}/documents/upload`, {
        method: "POST",
        body: formData,
        signal: timeout.signal,
        cache: "no-store"
      });
      if (!response.ok) throw new Error(await responseErrorMessage(response));
      return response.json() as Promise<DocumentRead>;
    } catch (err) {
      throw normalizeRequestError(err, UPLOAD_TIMEOUT_MS, "Upload and PDF extraction");
    } finally {
      timeout.clear();
    }
  },
  analyzeDocument: (documentId: string) =>
    request<AnalysisResult>(`/documents/${documentId}/analyze`, { method: "POST", timeoutMs: ANALYSIS_TIMEOUT_MS }),
  getAnalysis: (documentId: string) => request<AnalysisResult>(`/documents/${documentId}/analysis`),
  deleteDocument: async (documentId: string) => {
    const response = await fetch(`${apiBase()}/documents/${documentId}`, { method: "DELETE" });
    if (!response.ok) throw new Error(await responseErrorMessage(response));
  },
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
    const response = await fetch(`${apiBase()}/dictionary/items/${itemId}`, { method: "DELETE" });
    if (!response.ok) throw new Error(await response.text());
  },
  getProfile: () => request<UserProfile>("/profile", { timeoutMs: PROFILE_TIMEOUT_MS }),
  updateProfile: (payload: Partial<Omit<UserProfile, "id" | "created_at">>) =>
    request<UserProfile>("/profile", { method: "PATCH", body: JSON.stringify(payload) }),
  parseTranscript: (payload: { content: string; source_name: string }) =>
    request<TranscriptResponse>("/video/transcripts/parse", { method: "POST", body: JSON.stringify(payload) }),
  fetchYouTubeTranscript: (payload: { url: string; languages?: string[] }) =>
    request<TranscriptResponse>("/video/transcripts/youtube", { method: "POST", body: JSON.stringify(payload) })
};
