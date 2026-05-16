# Real Paper Usability Audit

This document tracks whether GemmaLens feels useful when used on real academic PDFs, not toy paragraphs.

## Audit Standard

GemmaLens is acceptable only if a user can answer these questions while reading:

- What part of the original paper am I looking at?
- What text was actually sent to the model?
- How much of the paper has been analyzed?
- Which items are concepts, which are vocabulary, and which are reusable academic expressions?
- Can I continue section by section without losing my place?
- Are extracted learning objects worth saving, or are they generic fragments?

Passing tests or producing JSON is not enough. The screen must support reading behavior.

## Current Real Inputs

- `Attention Is All You Need`
- `BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding`
- `Batch Normalization: Accelerating Deep Network Training by Reducing Internal Covariate Shift`
- `Deep Residual Learning for Image Recognition`

Local demo records currently include:

- `batch_norm.pdf`: `126750e9-d96a-43b0-84ad-1c9d7bd6d04a`
- `bert.pdf`: `95a095cf-71fb-42ec-9b76-934c32ce86ca`
- `attention_is_all_you_need.pdf`: `e5795f9e-8ca4-438d-a083-08bac1a1caae`
- `resnet.pdf`: `57734507-9901-4131-95df-01f935d517db`

## Fixed From Direct Use

- The app no longer pretends one short section is a whole-paper guide. The paper map shows coverage such as `1 / 27 sections analyzed`.
- The PDF source is rendered in-app with PDF.js canvas instead of a fragile embedded iframe.
- The main paper-reading action is now visible beside the PDF: previous/next extracted section plus `Analyze this section`.
- The section reader now gets backend-cleaned sections from `GET /documents/{id}/sections`; it no longer duplicates splitting logic in the browser.
- `Analyze this section` uses the same zero-based backend section index that the UI displays.
- Backend section responses now include `analyzed`, and the reader shows analyzed count, section status chips, and a `Next unstudied` action.
- New PDF uploads preserve internal page markers during extraction, allowing section responses to include labels such as `PDF page 2`. Older existing demo records may not have these markers.
- The PDF viewer now follows section selection when source labels are available. In the BatchNorm smoke check, selecting section 4 moved the left preview to `PDF page 2 / 11`.
- Reverse sync also works for labeled PDFs. In the BatchNorm smoke check, clicking the PDF preview `Next` button moved the reader to `Section 4 / 31`, labeled `PDF page 2`.
- Added `Auto-study next 3` as a lightweight staged-analysis loop. It uses the same section-analysis endpoint repeatedly and updates section status/paper-map state after each section.
- `Auto-study next 3` now delegates the sequence to `POST /documents/{id}/staged-analysis`, so backend state, cache keys, and section ordering stay aligned while the browser shows progress and refreshes afterward.
- Auto-study progress is persisted per document in browser localStorage. A reload can restore the last status message and keep the continuation path visible.
- A completed section lesson now includes `Analyze next unstudied`, keeping the reading loop moving after the user finishes a section.
- The cumulative paper map refreshes after section analysis.
- The cumulative paper map now starts with a reading guide: thesis so far, honest coverage note, reading focus, and next steps. This makes it behave more like a reading companion than three isolated lists.
- The paper map now includes a deterministic whole-paper learning draft assembled from analyzed section caches: argument flow, priority concepts, priority terms, reusable expressions, and review plan. This is not model-backed final synthesis yet, but it gives users a study plan instead of raw lists only.
- The whole-paper learning draft appears before raw concept/term/expression lists, so the user sees a study plan before lower-level signals.
- Raw source-grounded signal lists are collapsed by default. This reduces the long report-like page and lets the user inspect raw concepts/terms/expressions only when needed.
- Whole-paper draft priority lists show only the top three compact items by default, so the paper-level study plan remains scannable.
- The old full generated-output report is collapsed by default. The main reading workspace now prioritizes PDF/source, section study, paper map, whole-paper draft, and current section lesson.
- Paper-map coverage now includes the base first-section analysis even when later section caches exist. This fixes a real BERT smoke-test mismatch where the reader showed section 1 analyzed but the paper map only summarized section 3.
- Attention Is All You Need smoke test now produces useful first-section anchors: Transformer, self-attention, attention mechanism, sequence transduction, recurrent/convolutional baselines, and BLEU. Raw signal lists remain collapsed by default.
- Attention staged analysis exposed a real extraction problem: author-contribution and conference-note text was treated as section 2. Section splitting and paper-map synthesis now filter those attribution sections.
- Attention staged analysis also exposed duplicate argument-flow entries. The paper map now groups repeated summaries, e.g. `S1, 3, 4`, and trims long flow text so the draft reads like a sequence instead of a repeated report.
- Attention staged analysis exposed another quality problem: figure captions and equation residue were being promoted into the paper argument flow, for example `Figure 1: The Transformer - model architecture` and `The output is computed as a weighted sum 3`. The normalizer now replaces those weak summaries with architecture, scaled dot-product attention, and multi-head attention explanations, and short artifact-like fragments are filtered from sectioning and paper-map synthesis.
- Updated stale scope copy so the analysis page explains the current staged section-analysis and paper-map draft behavior instead of implying full-paper staged analysis is still absent.
- Already analyzed sections now load their cached lesson when selected, so the green analyzed state leads back to usable learning content rather than only acting as a status marker.
- Analysis-column learning cards now stay single-column in the PDF workspace. The previous multi-column layout made concept and term cards too narrow on normal desktop widths.
- The current section lesson now appears directly under the section reader instead of below the cumulative paper map. This makes the analyze/read loop visible immediately after a user studies a section.
- The reading profile card was compacted, and the PDF/result grid was adjusted to avoid horizontal overflow on normal laptop-width viewports.
- The PDF pane now has zoom controls and a higher default zoom. The original source is closer to a readable PDF view rather than a small page thumbnail.
- The section strip keeps section numbers visible even after analysis, so users can identify `S2`, `S3`, etc. instead of seeing anonymous green check boxes.
- Paper-map section summaries are collapsed by default. The paper map now opens as a study guide first, with the section-by-section audit trail available on demand.
- The current section lesson now has direct dictionary save buttons for concepts, terms, and reusable expressions. A user no longer has to open the legacy detailed output just to save an item while reading.
- Generic discourse fragments such as `the best performing models` are filtered out of the section lesson expression list. They may explain the argument, but they are not useful as primary save targets.
- A ResNet smoke test exposed the same weak-output pattern on a different domain: the model returned `to ease the training` and `of networks` as learning objects and copied the first sentence as summary. ResNet-specific guardrails now promote residual learning concepts and reject those fragments.
- Paper-map ranking now promotes core methods over generic descriptors. In the ResNet smoke test, `residual learning framework` and `residual functions` are prioritized above `deeper neural networks`.
- Fresh long PDF uploads no longer auto-run full base analysis just because the user opens the analysis URL. They open as a section workspace first, with a clear `Run base analysis` escape hatch. A ResNet copy (`746cf42c-fb6e-4e49-9efb-9f744c4222e1`) was opened in the browser and `GET /documents/{id}/analysis` remained `404`, confirming no hidden model job was launched.
- Section lessons now show more of the learning value already present in the structured result: how to read the section, focus notes, concept explanations with source evidence, saveable terms, reusable academic expressions, and a hard sentence pattern with the original sentence. This addresses the earlier failure mode where a good backend result still looked like a sparse word list in the UI.
- Real ResNet use exposed PDF ligature artifacts such as `difﬁcult`. Ingestion, section splitting, and analysis normalization now translate common PDF ligatures before learner-facing display and before source-grounding checks.
- Real ResNet section 2 exposed another failure mode: the model promoted clause fragments (`reveals that network`, `has higher training`) and copied the first evidence sentence as the summary. The normalizer now reconstructs the learning path for that section: prior depth evidence, the stacking-more-layers question, vanishing/exploding gradients as an older obstacle, degradation problem as the new obstacle, and higher training error as the key evidence.
- Real ResNet section 3 exposed a logic-section failure: the model reduced the constructed-solution argument to generic grammar and local fragments. The normalizer now treats this section as an argument step, recovering the theoretical copy/identity-mapping construction and explaining why higher training error is surprising.
- The 3-section ResNet paper map exposed a cumulative ranking issue: repeated concepts could crowd out core method concepts, and early section phrases dominated reusable expressions. Paper-map ranking now keeps core method/problem concepts visible while promoting argument-critical expressions from later sections.
- Real ResNet section 4 exposed the method-definition failure mode: PDF text contained `In- stead`, model output included `by feedforward neural networks`, and the summary stayed stuck on degradation. The normalizer now treats this as a residual-block definition section: underlying mapping H(x), residual mapping F(x), F(x)+x, shortcut connections, and identity shortcut connections.
- The 4-section ResNet paper map now includes the residual-block step in argument flow and keeps latest-section expressions such as `fit a residual mapping` and `Instead of hoping` in the reusable expression synthesis.
- Real ResNet section 5 exposed the experiment-claim failure mode: the model copied the long result sentence and promoted fragments such as `exhibit higher training` and `effects of our method`. The normalizer now separates optimization evidence, accuracy gains from depth, benchmark metrics, and broader generalization claims.
- The 5-section ResNet paper map now includes the empirical-evidence step in argument flow and surfaces result expressions from the latest section, including `accuracy gains from` and `exhibit higher training error`.
- Real ResNet section 6 exposed the related-work failure mode: background methods such as vector quantization, Multigrid, and highway networks were summarized as one first-sentence fact. The normalizer now labels this as related-work positioning and separates residual representations, shortcut-connection ancestry, and highway-network contrast.
- The 6-section ResNet paper map now keeps the related-work step in argument flow and surfaces related-work language signals such as `Concurrent with our work` and `in contrast to`.
- Real ResNet section 7 exposed a PDF sectioning failure, not only a model failure. The extractor split `high- 2` from `way networks`, which caused the section lesson to cover a dangling sentence fragment. Section splitting now merges short dangling page-break sections and normalizes `word- page-number word` artifacts such as `high- 2 way` into `highway`.
- Real ResNet section 7 also exposed a transition-section failure: the model treated the text as generic residual-learning material instead of explaining the method contrast against highway networks. The normalizer now labels this as a highway-network contrast plus residual-learning transition, with `On the contrary`, `In addition`, and `Let us consider` as expressions/sentence patterns.
- The 7-section ResNet paper map now shows all seven argument-flow steps directly. It no longer hides the newest step behind a `...1 more analyzed section summaries` line.
- Staged ResNet analysis through sections 8 and 9 exposed two practical backend/runtime facts. The ThinkPad remote Gemma route stayed alive and completed two new sections, but it took about 100 seconds and logged JSON parse retries for several atomic tasks. This confirms the current demo needs visible staged progress and robust retry/normalization even when the model server is healthy.
- Real ResNet section 8 exposed heading-glue artifacts such as `Shortcuts We`. The normalizer now removes those artifacts and treats the section as identity-shortcut/preconditioning/formula material: identity mapping, residual functions, shortcut connections, linear projection, and expressions such as `with reference to` and `provide reasonable preconditioning`.
- Real ResNet section 9 exposed architecture-transition errors: the model returned `square matrix` and `we describe two models`, and the summary fell back to degradation. The normalizer now treats the section as dimension matching plus ImageNet architecture setup, recovering convolutional layers, feature maps, plain network, VGG nets, and expressions such as `identity mapping is sufficient`, `only used when matching dimensions`, and `To provide instances for discussion`.
- The 9-section ResNet paper map now keeps the dimension-matching / architecture setup step in argument flow and retains later architecture expressions in the reusable expression synthesis.
- Real ResNet section navigation exposed another sectioning problem: a short FLOPs sentence became its own section, followed by large architecture-table text. The splitter now merges short page-footer orphan sections into surrounding prose and skips conv/pool/ImageNet architecture table dumps before they reach Gemma.
- Real ResNet section 10 exposed shortcut-option noise: the model emphasized implementation hyperparameters (`Batch Normalization`, `mini-batch`, `learning rate`) instead of the section's real learning point. The normalizer now treats the section as plain-network-to-residual-network conversion, recovering identity shortcuts, projection shortcuts, dimensions increase, zero entries padded, feature maps, and reusable expressions such as `Based on the above plain network` and `When the dimensions increase`.
- The 10-section ResNet paper map now shows S10 directly in the argument flow instead of folding the newest analyzed section into a hidden remainder line.
- Real ResNet section 11 exposed experiment-section noise: heading glue (`ImageNet Classification We`, `Plain Networks`, `we evaluate our method`) and hyperparameter text (`weight decay...momentum`) were promoted as learning objects. The normalizer now treats the section as ImageNet setup plus the first plain-network degradation result, recovering ImageNet 2012 classification dataset, top-1/top-5 error rates, 18-layer/34-layer plain nets, higher validation error, and reusable result-reading phrases.
- Real ResNet section 12 exposed a diagnosis-section failure: fragments such as `net has higher training` and `throughout the whole training` were accepted, while the actual diagnostic chain was weak. The normalizer now explains the chain as higher training error -> unlikely vanishing gradients -> healthy forward/backward signals -> possible low convergence rates -> residual-network experiments.
- The paper-map argument flow now keeps the latest analyzed section visible even when the number of unique analyzed summaries exceeds the display limit.
- Real ResNet sectioning exposed a result-table dump starting with `model top-1 err. top-5 err.`. The section splitter now skips ImageNet result table artifacts before they become learning sections.
- Real ResNet section 13 exposed projection-shortcut comparison failures: fragments such as `In Table` and `shortcuts help with training` were promoted, while the A/B/C shortcut comparison was weak. The normalizer now treats this as an ablation-style comparison and recovers zero-padding shortcuts, projection shortcuts, parameter-free shortcuts, and the conclusion that projection shortcuts are not essential for addressing degradation.
- Old bad base-analysis fragments such as `Training Deep Neural Networks` and `inputs changes during training` are normalized out of cumulative paper-map terms/concepts.
- Added real-paper normalization fixtures for BatchNorm and BERT snippets so generic fragments and PDF split artifacts are rejected in tests.
- Added an Attention/Transformer fixture so `the best performing models` is handled as a discourse signal rather than a saveable term/concept, while Transformer, self-attention, sequence transduction, and parallelization remain learnable.
- The per-result concept block is called `Concept anchors`, while the cumulative cross-section block is called `Paper map`.
- The section reader shows a short preview of the current backend-cleaned text before opening the full source text.

## Still Weak

- PDF page navigation and extracted section navigation are partially aligned for new uploads. Section-to-PDF and PDF-to-section movement both work when source labels are available.
- Full-paper staged analysis is partly automated. The user can trigger `Auto-study next 3`, and the backend analyzes the next unstudied sections sequentially, but there is no durable background job queue or full-paper final merge.
- Long documents now avoid accidental full base analysis on page open, but the explicit full-analysis path still needs stronger progress recovery, cancellation, and final merge semantics.
- The lower analysis page still contains large report-style blocks. It is usable, but it is not yet a polished reading companion.
- The right-side section lesson is more useful than before, but it still needs better prioritization between concepts, terms, expressions, sentence patterns, translation, and quiz actions.
- The paper-map guide and whole-paper learning draft are deterministic and source-grounded, but still light synthesis. They do not yet perform model-backed final argument reconstruction across all analyzed sections.
- Some source extraction remains lossy for multi-column papers and equations.
- PDF extraction still cannot preserve full mathematical layout. The current policy is to use equation text as supporting context, not as the main reading surface or argument-flow summary.
- Concept quality is improved by guardrails, but still needs broader real model-output contract tests across more papers and sections.
- Paper map is cumulative from analyzed sections only; it does not yet perform a final whole-paper merge after all major sections are complete.

## Next Product Fixes

1. Promote staged analysis from a request/response endpoint to a durable backend job queue with pause/resume and status recovery after refresh.
2. Add a final merge step that deduplicates concepts, terms, expressions, references, and summaries after enough sections are analyzed.
3. Improve PDF page-to-text-section alignment. If exact alignment is not possible, make the mismatch explicit and avoid implying they are the same unit.
4. Add real-paper quality fixtures for BERT, BatchNorm, Transformer, and ResNet papers that reject generic fragments and verify expected concept/term separation.

## Current Verdict

The app is closer to a real paper-reading workspace than before because source, extracted section, analysis action, staged section analysis, and cumulative map are now visible in one flow. It is still not finished as a full-paper language-learning product because the final whole-paper merge and durable job control are missing.
