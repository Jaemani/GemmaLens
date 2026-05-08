import type { AnalysisResult, DocumentListItem, DocumentRead } from "./types";

export const DEMO_DOCUMENT_ID = "demo";

export const demoDocument: DocumentRead = {
  id: DEMO_DOCUMENT_ID,
  title: "Sleep and learning excerpt",
  source_type: "demo",
  content:
    "Although previous studies have suggested a correlation between sleep deprivation and reduced cognitive performance, the extent to which these findings generalize across real-world learning environments remains unclear. To address this gap, we analyze longitudinal study logs collected from undergraduate students over a six-week period.",
  created_at: new Date(0).toISOString()
};

export const demoDocuments: DocumentListItem[] = [
  {
    id: DEMO_DOCUMENT_ID,
    title: demoDocument.title,
    source_type: demoDocument.source_type,
    preview: demoDocument.content.slice(0, 140),
    created_at: demoDocument.created_at
  }
];

export const demoAnalysis: AnalysisResult = {
  document_id: DEMO_DOCUMENT_ID,
  domain: {
    primary_domain: "education",
    secondary_domains: ["cognitive science", "academic research"],
    document_type: "paper",
    confidence: 0.86
  },
  difficulty: {
    overall_level: "C1",
    lexical_difficulty: 7,
    syntax_difficulty: 8,
    domain_difficulty: 6,
    reason: "Dense academic syntax combines concession, uncertainty, and method framing."
  },
  terms: [
    {
      term: "sleep deprivation",
      meaning: "a state of not getting enough sleep",
      domain_relevance: "high",
      difficulty: "medium",
      source_sentence:
        "Although previous studies have suggested a correlation between sleep deprivation and reduced cognitive performance, the extent to which these findings generalize across real-world learning environments remains unclear.",
      should_save: true
    },
    {
      term: "cognitive performance",
      meaning: "how well the mind performs tasks like memory, attention, and reasoning",
      domain_relevance: "high",
      difficulty: "medium",
      source_sentence:
        "Although previous studies have suggested a correlation between sleep deprivation and reduced cognitive performance, the extent to which these findings generalize across real-world learning environments remains unclear.",
      should_save: true
    },
    {
      term: "generalize",
      meaning: "apply findings from one context to other contexts",
      domain_relevance: "medium",
      difficulty: "hard",
      source_sentence:
        "Although previous studies have suggested a correlation between sleep deprivation and reduced cognitive performance, the extent to which these findings generalize across real-world learning environments remains unclear.",
      should_save: true
    },
    {
      term: "real-world learning environments",
      meaning: "actual educational settings outside controlled experiments",
      domain_relevance: "high",
      difficulty: "hard",
      source_sentence:
        "Although previous studies have suggested a correlation between sleep deprivation and reduced cognitive performance, the extent to which these findings generalize across real-world learning environments remains unclear.",
      should_save: true
    },
    {
      term: "longitudinal study",
      meaning: "research that observes the same subjects over time",
      domain_relevance: "high",
      difficulty: "hard",
      source_sentence:
        "To address this gap, we analyze longitudinal study logs collected from undergraduate students over a six-week period.",
      should_save: true
    }
  ],
  phrases: [
    {
      phrase: "previous studies have suggested",
      function: "claim",
      explanation: "Introduces existing evidence without making a fully certain claim.",
      source_sentence:
        "Although previous studies have suggested a correlation between sleep deprivation and reduced cognitive performance, the extent to which these findings generalize across real-world learning environments remains unclear."
    },
    {
      phrase: "the extent to which",
      function: "general",
      explanation: "Frames a question about degree or scope.",
      source_sentence:
        "Although previous studies have suggested a correlation between sleep deprivation and reduced cognitive performance, the extent to which these findings generalize across real-world learning environments remains unclear."
    },
    {
      phrase: "remains unclear",
      function: "limitation",
      explanation: "Marks an unresolved research problem.",
      source_sentence:
        "Although previous studies have suggested a correlation between sleep deprivation and reduced cognitive performance, the extent to which these findings generalize across real-world learning environments remains unclear."
    },
    {
      phrase: "to address this gap",
      function: "method",
      explanation: "Connects the research gap to the authors' method.",
      source_sentence:
        "To address this gap, we analyze longitudinal study logs collected from undergraduate students over a six-week period."
    }
  ],
  sentences: [
    {
      sentence:
        "Although previous studies have suggested a correlation between sleep deprivation and reduced cognitive performance, the extent to which these findings generalize across real-world learning environments remains unclear.",
      core_structure: "Although A, B remains unclear.",
      simplified_version: "Past studies found a link, but we still do not know if it applies in real classrooms.",
      korean_explanation: "'Although' 절은 배경 연구를 양보로 제시하고, 주절은 아직 불명확한 점을 말합니다.",
      difficulty_reason: "Long noun phrases and embedded question structure make the main claim hard to locate."
    },
    {
      sentence:
        "To address this gap, we analyze longitudinal study logs collected from undergraduate students over a six-week period.",
      core_structure: "To address this gap, we analyze X collected from Y over Z.",
      simplified_version: "We study six weeks of logs from undergraduates to investigate the gap.",
      korean_explanation: "'To address this gap'은 연구 목적을 나타내고, 주절은 분석 대상을 설명합니다.",
      difficulty_reason: "Method phrase, passive reduced clause, and time expression are packed into one sentence."
    }
  ],
  summaries: {
    one_line: "The text studies whether sleep-related cognitive findings apply to real learning settings.",
    simple:
      "Researchers know sleep loss may reduce thinking performance, but they are testing whether that finding holds in real undergraduate learning data.",
    academic:
      "The passage identifies a generalizability gap in sleep deprivation and cognitive performance research, then proposes longitudinal analysis of undergraduate study logs as the method.",
    study_notes: [
      "Use 'remains unclear' to state a research gap.",
      "Use 'to address this gap' to move from problem to method.",
      "Look for the main clause after long 'Although' openings."
    ]
  }
};
