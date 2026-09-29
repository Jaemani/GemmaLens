import type { Page, Route } from "@playwright/test";
import { test as base, expect } from "@playwright/test";

export { expect };
export const test = base.extend({
  page: async ({ page, baseURL }, use) => {
    await page.route("**/*", async (route) => {
      const url = new URL(route.request().url());
      if (url.origin !== new URL(baseURL!).origin) return route.abort();
      return route.fallback();
    });
    await page.route("**/api/backend/**", (route) => {
      const path = new URL(route.request().url()).pathname.replace("/api/backend", "");
      if (path === "/profile") return fulfillJson(route, {
        id: "profile", display_name: "Learner", target_level: "B2", support_language: "Korean",
        learning_language: "English", auto_analyze_documents: false, onboarding_completed: true,
      });
      if (path === "/models/status") return fulfillJson(route, {
        provider: "mock", preset_id: "mock", preset_label: "Mock analysis", mock_fallback: true, demo_mode: true,
      });
      if (path === "/models/presets" || path === "/documents" || path === "/dictionary/items") return fulfillJson(route, []);
      if (path === "/video/local-library") return fulfillJson(route, { root: "", items: [] });
      if (path.endsWith("/paper-map")) return fulfillJson(route, {
        document_id: path.split("/")[2], total_sections: 1, analyzed_sections: [1],
        guide: { title: "Reading guide", thesis_so_far: "Ready.", coverage_note: "1 / 1", reading_focus: [], next_steps: [] },
        synthesis: { status: "complete", argument_flow: [], priority_concepts: [], priority_terms: [], reusable_expressions: [], review_plan: [] },
        top_concepts: [], top_terms: [], top_phrases: [], section_summaries: [],
      });
      return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "No fixture for this request" }) });
    });
    await use(page);
  },
});

export const mockTranscript = {
  source_type: "subtitle",
  source_id: "movie-dialogue.srt",
  title: "movie-dialogue.srt",
  warning: null,
  plain_text: "You're not gonna get away with this.\nI should have told you earlier.\nThis changes everything.",
  segments: [
    {
      index: 1,
      start: 1,
      duration: 2.5,
      end: 3.5,
      text: "You're not gonna get away with this."
    },
    {
      index: 2,
      start: 4,
      duration: 2.2,
      end: 6.2,
      text: "I should have told you earlier."
    },
    {
      index: 3,
      start: 7,
      duration: 3,
      end: 10,
      text: "This changes everything."
    }
  ]
};

export const mockAnalysis = {
  document_id: "video-doc",
  domain: {
    primary_domain: "spoken English",
    secondary_domains: ["movie dialogue"],
    document_type: "article",
    confidence: 0.9
  },
  difficulty: {
    overall_level: "B2",
    lexical_difficulty: 5,
    syntax_difficulty: 4,
    domain_difficulty: 3,
    reason: "Casual spoken expressions and implied tone require context."
  },
  terms: [
    {
      term: "get away with this",
      meaning: "avoid consequences",
      domain_relevance: "high",
      difficulty: "medium",
      source_sentence: "You're not gonna get away with this.",
      should_save: true,
      learning_priority: "must_review",
      reason: "Common spoken phrase for consequences.",
      context_meaning: "You will not avoid punishment for this.",
      general_meaning: "avoid consequences",
      confidence: 0.9,
      user_state: "suggested"
    }
  ],
  phrases: [
    {
      phrase: "should have told",
      function: "general",
      explanation: "Expresses regret about not saying something earlier.",
      source_sentence: "I should have told you earlier.",
      learning_priority: "useful",
      reason: "Common regret pattern.",
      context_meaning: "I regret not telling you earlier.",
      confidence: 0.9,
      user_state: "suggested"
    }
  ],
  sentences: [
    {
      sentence: "You're not gonna get away with this.",
      core_structure: "You are not going to + verb phrase.",
      simplified_version: "You will not avoid consequences.",
      korean_explanation: "상대가 처벌이나 책임을 피하지 못할 것이라는 의미입니다.",
      difficulty_reason: "Casual reduction and idiomatic phrase."
    }
  ],
  summaries: {
    one_line: "A confrontational movie dialogue with idiomatic spoken expressions.",
    simple: "Someone warns another person that they cannot avoid consequences.",
    academic: "The scene uses informal speech and idiomatic language to signal conflict.",
    study_notes: ["gonna = going to", "get away with = avoid consequences"]
  },
  quality_warnings: []
};

export async function mockVideoApi(page: Page) {
  await page.route("**/video/transcripts/parse", (route: Route) => fulfillJson(route, mockTranscript));
  await page.route("**/video/transcripts/youtube", (route: Route) => fulfillJson(route, { ...mockTranscript, source_type: "youtube", source_id: "dQw4w9WgXcQ" }));
  await page.route("**/documents", async (route: Route) => {
    if (route.request().method() === "POST") {
      await fulfillJson(route, {
        id: "video-doc",
        title: "Video transcript",
        source_type: "transcript",
        content: mockTranscript.plain_text,
        created_at: new Date(0).toISOString()
      });
      return;
    }
    await route.fallback();
  });
  await page.route("**/documents/video-doc/analyze", (route: Route) => fulfillJson(route, mockAnalysis));
  await page.route("**/documents/video-doc/analysis", (route: Route) => fulfillJson(route, mockAnalysis));
  await page.route("**/dictionary/items", (route: Route) => {
    if (route.request().method() === "POST") {
      return fulfillJson(route, {
        id: "saved-item",
        item_type: "term",
        text: "get away with this",
        meaning: "avoid consequences",
        source_sentence: "You're not gonna get away with this.",
        document_id: "video-doc",
        notes: null,
        encounter_count: 1,
        view_count: 0,
        last_viewed_at: null,
        created_at: new Date(0).toISOString()
      });
    }
    return fulfillJson(route, []);
  });
}

function fulfillJson(route: Route, body: unknown) {
  return route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(body)
  });
}
