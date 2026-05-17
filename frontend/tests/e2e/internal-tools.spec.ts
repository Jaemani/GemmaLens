import { expect, test } from "@playwright/test";
import { mockAnalysis } from "./fixtures";

test("internal experiment route is not part of the learner app", async ({ page }) => {
  await page.goto("/experiments");

  await expect(page).toHaveURL(/\/guide$/);
  await expect(page.getByRole("heading", { name: "Experiment dashboard" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "How to use GemmaLens" })).toBeVisible();
});

test("real analysis pages do not expose experiment controls", async ({ page }) => {
  await page.route("**/documents/real-doc", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "real-doc",
        title: "Real document",
        source_type: "text",
        content: "You're not gonna get away with this.",
        has_original_file: false,
        created_at: new Date(0).toISOString()
      })
    })
  );
  await page.route("**/documents/real-doc/analysis", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ...mockAnalysis, document_id: "real-doc" })
    })
  );

  await page.goto("/analysis/real-doc");

  await expect(page.getByText("A/B test panel")).toHaveCount(0);
  await expect(page.getByText("User-fit mode")).toHaveCount(0);
  await expect(page.getByText("spoken English")).toBeVisible();
});

test("document workspace prepares first page before showing paper map", async ({ page }) => {
  const pageCalls: number[] = [];
  const sections = [
    {
      index: 0,
      section_number: 1,
      total_sections: 2,
      text: "Abstract This first section explains the main contribution.",
      preview: "Abstract This first section explains the main contribution.",
      char_count: 58,
      analyzed: false,
      source_label: "PDF page 1",
      title: "Abstract",
      continuation: false
    },
    {
      index: 1,
      section_number: 2,
      total_sections: 2,
      text: "1 Introduction This second section introduces background.",
      preview: "1 Introduction This second section introduces background.",
      char_count: 56,
      analyzed: false,
      source_label: "PDF page 1",
      title: "1 Introduction",
      continuation: false
    }
  ];

  await page.route(/\/documents\/first-section-doc$/, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "first-section-doc",
        title: "First section doc",
        source_type: "pdf",
        content: sections.map((section) => section.text).join("\n\n"),
        has_original_file: false,
        created_at: new Date(0).toISOString()
      })
    })
  );
  await page.route(/\/documents\/first-section-doc\/sections$/, (route) => {
    const body = sections.map((section) => ({
      ...section,
      analyzed: pageCalls.includes(1)
    }));
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
  await page.route("**/profile", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "profile",
        display_name: "Learner",
        target_level: "B2",
        support_language: "Korean",
        learning_language: "English",
        auto_analyze_documents: true,
        onboarding_completed: true,
        created_at: new Date(0).toISOString()
      })
    })
  );
  await page.route(/\/documents\/first-section-doc\/sections\/\d+\/analysis$/, (route) => {
    if (!pageCalls.includes(1)) {
      return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "not ready" }) });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ...mockAnalysis, document_id: "first-section-doc" })
    });
  });
  await page.route(/\/documents\/first-section-doc\/pages\/\d+\/analyze$/, async (route) => {
    const pageNumber = Number(route.request().url().match(/pages\/(\d+)\/analyze/)?.[1] ?? 0);
    pageCalls.push(pageNumber);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        document_id: "first-section-doc",
        total_pages: 1,
        total_sections: 2,
        requested_pages: [pageNumber],
        analyzed_pages: [pageNumber],
        analyzed_sections: [1, 2],
        skipped_sections: [],
        status: "completed",
        message: "Prepared page 1 with 2 section lesson(s)."
      })
    });
  });

  await page.goto("/analysis/first-section-doc");

  await expect(page.getByText("Preparing the first section lesson before opening the workspace.")).toBeVisible();
  await expect(page.getByText("Video lesson")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "A confrontational movie dialogue with idiomatic spoken expressions." })).toBeVisible();
  await expect.poll(() => pageCalls[0]).toBe(1);
});

test("upload flow prepares first page before opening reader", async ({ page }) => {
  const pageCalls: number[] = [];
  await page.route("**/documents/upload", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "uploaded-pdf",
        title: "attention.pdf",
        source_type: "pdf",
        content: "Abstract The Transformer is based on attention.",
        has_original_file: true,
        original_mime_type: "application/pdf",
        created_at: new Date(0).toISOString()
      })
    })
  );
  await page.route(/\/documents\/uploaded-pdf\/pages\/1\/analyze$/, (route) => {
    pageCalls.push(1);
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        document_id: "uploaded-pdf",
        total_pages: 1,
        total_sections: 1,
        requested_pages: [1],
        analyzed_pages: [1],
        analyzed_sections: [1],
        skipped_sections: [],
        status: "completed",
        message: "Prepared page 1."
      })
    });
  });
  await page.route(/\/documents\/uploaded-pdf$/, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "uploaded-pdf",
        title: "attention.pdf",
        source_type: "pdf",
        content: "Abstract The Transformer is based on attention.",
        has_original_file: true,
        original_mime_type: "application/pdf",
        created_at: new Date(0).toISOString()
      })
    })
  );
  await page.route(/\/documents\/uploaded-pdf\/sections$/, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          index: 0,
          section_number: 1,
          total_sections: 1,
          text: "Abstract The Transformer is based on attention.",
          preview: "Abstract The Transformer is based on attention.",
          char_count: 47,
          analyzed: true,
          source_label: "PDF page 1",
          title: "Abstract",
          continuation: false
        }
      ])
    })
  );
  await page.route(/\/documents\/uploaded-pdf\/sections\/0\/analysis$/, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ...mockAnalysis, document_id: "uploaded-pdf" })
    })
  );
  await page.route(/\/documents\/uploaded-pdf\/paper-map$/, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        document_id: "uploaded-pdf",
        total_sections: 1,
        analyzed_sections: [1],
        guide: { title: "Reading guide", thesis_so_far: "Ready.", coverage_note: "1 / 1 sections analyzed.", reading_focus: [], next_steps: [] },
        synthesis: { status: "complete", argument_flow: [], priority_concepts: [], priority_terms: [], reusable_expressions: [], review_plan: [] },
        top_concepts: [],
        top_terms: [],
        top_phrases: [],
        section_summaries: []
      })
    })
  );
  await page.route("**/profile", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "profile",
        display_name: "Learner",
        target_level: "B2",
        support_language: "Korean",
        learning_language: "English",
        auto_analyze_documents: false,
        onboarding_completed: true,
        created_at: new Date(0).toISOString()
      })
    })
  );

  await page.goto("/documents");
  const fileChooserPromise = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Choose file", exact: true }).click();
  const chooser = await fileChooserPromise;
  await chooser.setFiles({
    name: "attention.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF mock")
  });

  await expect(page.getByText("Preparing the first page lesson so the reader opens ready...")).toBeVisible();
  await expect.poll(() => pageCalls.length).toBe(1);
  await expect(page).toHaveURL(/\/analysis\/uploaded-pdf$/);
});

test("pdf viewer waits until the first page lesson is ready", async ({ page }) => {
  let resolvePageAnalyze: (() => void) | null = null;
  const pageAnalyzeStarted = new Promise<void>((resolve) => {
    resolvePageAnalyze = resolve;
  });
  const sections = [
    {
      index: 0,
      section_number: 1,
      total_sections: 1,
      text: "Abstract This first section explains the main contribution.",
      preview: "Abstract This first section explains the main contribution.",
      char_count: 58,
      analyzed: false,
      source_label: "PDF page 1",
      title: "Abstract",
      continuation: false
    }
  ];
  let ready = false;

  await page.route(/\/documents\/delayed-pdf$/, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "delayed-pdf",
        title: "Delayed PDF",
        source_type: "pdf",
        content: sections[0].text,
        has_original_file: true,
        original_mime_type: "application/pdf",
        created_at: new Date(0).toISOString()
      })
    })
  );
  await page.route(/\/documents\/delayed-pdf\/sections$/, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(sections.map((section) => ({ ...section, analyzed: ready })))
    })
  );
  await page.route("**/profile", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "profile",
        display_name: "Learner",
        target_level: "B2",
        support_language: "Korean",
        learning_language: "English",
        auto_analyze_documents: false,
        onboarding_completed: true,
        created_at: new Date(0).toISOString()
      })
    })
  );
  await page.route(/\/documents\/delayed-pdf\/pages\/1\/analyze$/, async (route) => {
    resolvePageAnalyze?.();
    await new Promise((resolve) => setTimeout(resolve, 500));
    ready = true;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        document_id: "delayed-pdf",
        total_pages: 1,
        total_sections: 1,
        requested_pages: [1],
        analyzed_pages: [1],
        analyzed_sections: [1],
        skipped_sections: [],
        status: "completed",
        message: "Prepared page 1 with 1 section lesson."
      })
    });
  });
  await page.route(/\/documents\/delayed-pdf\/sections\/0\/analysis$/, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ...mockAnalysis, document_id: "delayed-pdf" })
    })
  );
  await page.route(/\/documents\/delayed-pdf\/paper-map$/, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        document_id: "delayed-pdf",
        total_sections: 1,
        analyzed_sections: [1],
        guide: { title: "Reading guide", thesis_so_far: "Ready.", coverage_note: "1 / 1 sections analyzed.", reading_focus: [], next_steps: [] },
        synthesis: { status: "complete", argument_flow: [], priority_concepts: [], priority_terms: [], reusable_expressions: [], review_plan: [] },
        top_concepts: [],
        top_terms: [],
        top_phrases: [],
        section_summaries: []
      })
    })
  );

  await page.goto("/analysis/delayed-pdf");
  await pageAnalyzeStarted;

  await expect(page.getByText("Preparing the first page lesson before opening the PDF viewer.")).toBeVisible();
  await expect(page.getByText("Original PDF")).toHaveCount(0);

  await expect(page.getByText("Original PDF")).toBeVisible();
  await expect(page.getByText("A confrontational movie dialogue with idiomatic spoken expressions.")).toBeVisible();
});

test("document section navigator moves by PDF page and highlights current page", async ({ page }) => {
  const sections = [
    {
      index: 0,
      section_number: 1,
      total_sections: 4,
      text: "Abstract This first page section explains the paper contribution.",
      preview: "Abstract This first page section explains the paper contribution.",
      char_count: 64,
      analyzed: true,
      source_label: "PDF page 1",
      title: "Abstract",
      continuation: false
    },
    {
      index: 1,
      section_number: 2,
      total_sections: 4,
      text: "1 Introduction This second page-local section introduces the background.",
      preview: "1 Introduction This second page-local section introduces the background.",
      char_count: 74,
      analyzed: true,
      source_label: "PDF page 1",
      title: "1 Introduction",
      continuation: false
    },
    {
      index: 2,
      section_number: 3,
      total_sections: 4,
      text: "2 Background This source page begins a new section.",
      preview: "2 Background This source page begins a new section.",
      char_count: 51,
      analyzed: true,
      source_label: "PDF page 2",
      title: "2 Background",
      continuation: false
    },
    {
      index: 3,
      section_number: 4,
      total_sections: 4,
      text: "2 Background continued This is another section on page two.",
      preview: "2 Background continued This is another section on page two.",
      char_count: 61,
      analyzed: false,
      source_label: "PDF page 2",
      title: "2 Background",
      continuation: true
    }
  ];

  await page.route(/\/documents\/nav-doc$/, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "nav-doc",
        title: "Navigation document",
        source_type: "pdf",
        content: sections.map((section) => section.text).join("\n\n"),
        has_original_file: false,
        created_at: new Date(0).toISOString()
      })
    })
  );
  await page.route(/\/documents\/nav-doc\/sections$/, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(sections) })
  );
  await page.route("**/profile", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "profile",
        display_name: "Learner",
        target_level: "B2",
        support_language: "Korean",
        learning_language: "English",
        auto_analyze_documents: false,
        onboarding_completed: true,
        created_at: new Date(0).toISOString()
      })
    })
  );
  await page.route(/\/documents\/nav-doc\/sections\/\d+\/analysis$/, (route) => {
    const sectionIndex = Number(route.request().url().match(/sections\/(\d+)\/analysis/)?.[1] ?? 0);
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...mockAnalysis,
        document_id: "nav-doc",
        summaries: {
          ...mockAnalysis.summaries,
          one_line: `Ready summary for section ${sectionIndex + 1}`
        }
      })
    });
  });
  await page.route(/\/documents\/nav-doc\/paper-map$/, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        document_id: "nav-doc",
        total_sections: 4,
        analyzed_sections: [1, 2, 3],
        map: {
          thesis_so_far: "Navigation test map.",
          coverage_note: "3 / 4 sections analyzed.",
          reading_focus: [],
          next_steps: []
        },
        concept_graph: [],
        vocabulary_plan: [],
        expression_plan: [],
        top_concepts: [],
        top_terms: [],
        top_phrases: [],
        section_summaries: []
      })
    })
  );

  await page.goto("/analysis/nav-doc");

  await expect(page.getByText("Page 1 · S1 · document section 1 / 4")).toBeVisible();
  await expect(page.locator('[data-current-page="true"]').getByText("Page 1", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Next PDF page" }).click();
  await expect(page.getByText("Page 2 · S1 · document section 3 / 4")).toBeVisible();
  await expect(page.locator('[data-current-page="true"]').getByText("Page 2", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Previous section" }).click();
  await expect(page.getByText("Page 1 · S2 · document section 2 / 4")).toBeVisible();
});
