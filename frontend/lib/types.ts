export type DocumentRead = {
  id: string;
  title: string;
  source_type: string;
  content: string;
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
};

export type DictionaryItem = {
  id: string;
  item_type: "term" | "phrase" | "sentence";
  text: string;
  meaning: string | null;
  source_sentence: string | null;
  document_id: string | null;
  notes: string | null;
  encounter_count: number;
  created_at: string;
};

export type ModelStatus = {
  provider: string;
  ollama_model: string;
  ollama_base_url: string;
  mlx_model_path: string;
  mlx_model_available: boolean;
  mock_fallback: boolean;
};
