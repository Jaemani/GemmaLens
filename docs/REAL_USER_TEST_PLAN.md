# Real-User Test Plan

## Goal

Find whether PaperLens helps real learners avoid manual copy/paste note-taking when reading hard academic PDFs or papers.

## Research Notes

- CEFR B2 users should be able to understand main ideas in complex technical text in their field; C1 users should handle demanding long texts but still need nuance support. Source: Council of Europe CEFR global scale, https://www.coe.int/en/web/common-European-framework-reference-languages/table-1-cefr-3.3-common-reference-levels-global-scale
- Web apps should store language preferences with standard language/locale concepts instead of hard-coding one language pair. Source: W3C language tags and locale identifiers, https://www.w3.org/TR/ltli/
- For formative usability, a small round of 5-8 participants is useful if the team fixes problems and repeats. Source: Nielsen Norman Group usability testing overview, https://media.nngroup.com/media/articles/attachments/Usability-Testing-101_SizeA4.pdf
- Internationalized UI should allow text expansion, different scripts, fonts, and layout direction. Source: web.dev internationalization guide, https://web.dev/learn/design/internationalization

## Personas To Test

1. Korean graduate student reading English papers.
2. Japanese undergraduate reading English technical reports.
3. Spanish speaker learning English through domain articles.
4. English speaker learning Korean or Japanese technical text.
5. Advanced reader who knows general English but not field vocabulary.
6. New learner who needs heavy support and onboarding.

## Test Tasks

1. Open app as a new user and set learning/support language.
2. Paste a short academic paragraph and run analysis.
3. Upload a text/markdown document.
4. Try a hard PDF with dense layout.
5. Save five terms and two sentence structures.
6. Return to dictionary and mark items as viewed.
7. Explain what the learner thinks they are currently studying.

## What To Measure

- Time to first successful analysis.
- Whether user understands model loading/progress state.
- Whether extracted terms are useful without manual copy/paste.
- Whether sentence decomposition helps more than translation.
- Whether language settings match user expectation.
- Whether hard PDF extraction fails gracefully.
- Whether saved/viewed items make study progress visible.

## Failure Signals

- User waits during analysis and thinks app is stuck.
- User cannot tell what to do after upload.
- PDF text extraction is empty or garbled.
- Terms are too obvious, too rare, or missing important domain vocabulary.
- User wants examples but saved item lacks source sentence.
- User cannot see what they already reviewed.

## Next Product Functions

- Per-document language pair and target level.
- More examples per saved term.
- Viewed/reviewed state and last-viewed timestamp.
- Domain memory: detect repeated fields such as LLM, medicine, law, economics.
- Similar-area term suggestions based on saved terms and document domain.
- Hard-PDF diagnostics: extraction quality score, page count, text coverage, warning when OCR is needed.

## Related Test Candidates

See `docs/AB_TEST_CANDIDATES.md` for the current A/B candidates focused on reducing cleanup time and improving dictionary quality.
