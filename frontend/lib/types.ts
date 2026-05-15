export type DocumentRead = {
  id: string;
  title: string;
  source_type: string;
  content: string;
  has_original_file: boolean;
  original_mime_type: string | null;
  created_at: string;
};

export type DocumentListItem = {
  id: string;
  title: string;
  source_type: string;
  preview: string;
  created_at: string;
};

export type AnalysisResult = {
  document_id: string;
  domain: {
    primary_domain: string;
    secondary_domains: string[];
    document_type: "paper" | "report" | "article" | "unknown";
    confidence: number;
  };
  difficulty: {
    overall_level: string;
    lexical_difficulty: number;
    syntax_difficulty: number;
    domain_difficulty: number;
    reason: string;
  };
  terms: Array<{
    term: string;
    meaning: string;
    domain_relevance: string;
    difficulty: string;
    source_sentence: string;
    should_save: boolean;
  }>;
  phrases: Array<{
    phrase: string;
    function: string;
    explanation: string;
    source_sentence: string;
  }>;
  concepts?: Array<{
    concept: string;
    explanation: string;
    source_sentence: string;
    related_terms: string[];
    why_it_matters: string;
    references: string[];
    learning_priority: string;
    confidence: number;
  }>;
  sentences: Array<{
    sentence: string;
    core_structure: string;
    simplified_version: string;
    korean_explanation: string;
    difficulty_reason: string;
  }>;
  summaries: {
    one_line: string;
    simple: string;
    academic: string;
    study_notes: string[];
  };
  quality_warnings?: string[];
};

export type PaperMapItem = {
  text: string;
  meaning: string;
  sections: number[];
  count: number;
};

export type PaperMap = {
  document_id: string;
  total_sections: number;
  analyzed_sections: number[];
  top_concepts: PaperMapItem[];
  top_terms: PaperMapItem[];
  top_phrases: PaperMapItem[];
  section_summaries: PaperMapItem[];
};

export type DictionaryItem = {
  id: string;
  item_type: "term" | "phrase" | "sentence" | "concept";
  text: string;
  meaning: string | null;
  source_sentence: string | null;
  document_id: string | null;
  notes: string | null;
  encounter_count: number;
  view_count: number;
  last_viewed_at: string | null;
  created_at: string;
};

export type UserProfile = {
  id: string;
  display_name: string;
  target_level: "B1" | "B2" | "C1" | "C2" | "domain-heavy" | "unknown";
  support_language: string;
  learning_language: string;
  onboarding_completed: boolean;
  created_at: string;
};

export type ModelStatus = {
  provider: "mock" | "mlx" | "ollama" | "remote";
  preset_id:
    | "mock"
    | "gemma4-e2b-mlx"
    | "gemma4-e4b-mlx"
    | "gemma4-e4b-ollama"
    | "gemma4-e2b-thinkpad"
    | "gemma4-e2b-thinkpad-q4"
    | "gemma4-e4b-thinkpad";
  preset_label: string;
  ollama_model: string;
  ollama_base_url: string;
  remote_gemma_model: string;
  remote_gemma_base_url: string;
  mlx_model_path: string;
  mlx_model_available: boolean;
  mock_fallback: boolean;
  demo_mode: boolean;
};

export type ModelPreset = {
  id: ModelStatus["preset_id"];
  label: string;
  runtime: ModelStatus["provider"];
  size: string;
  speed: string;
  availability: "ready" | "missing" | "external";
  description: string;
};

export type ModelConfigUpdate = {
  preset_id?: ModelStatus["preset_id"];
};

export type TranscriptSegment = {
  index: number;
  start: number;
  duration: number;
  end: number;
  text: string;
};

export type TranscriptResponse = {
  source_type: "subtitle" | "youtube";
  source_id: string | null;
  title: string | null;
  segments: TranscriptSegment[];
  plain_text: string;
  warning: string | null;
};

export type TranslationResponse = {
  source_language: string;
  target_language: string;
  source_text: string;
  translated_text: string;
  notes: string[];
};
