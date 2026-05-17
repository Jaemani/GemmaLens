# Real Source Audit

Last checked: 2026-05-17

This audit exists because matrix tests alone are not enough. GemmaLens must be checked against real extracted documents, real transcript paths, and learner-level output behavior.

## What Was Actually Checked

### Local DB PDF: Attention Is All You Need

Source in local database:

- `Attention is all you need.pdf`
- document id: `e6e7aff2-80dc-442b-ba73-4a6db3558105`
- extracted text length: `32930`

Section extraction result after cleanup:

- total logical sections: `23`
- no headingless sections
- no short heading-only sections
- no figure/table-leading sections
- front matter before Abstract is trimmed
- reference tail is not treated as a study section

Known continuation sections remain where the PDF page break splits a logical section:

- `3.2.2 Multi-Head Attention`
- `4 Why Self-Attention`
- `6.2 Model Variations`

Learning output audit:

- checked all `23` logical sections
- checked levels `B1`, `B2`, `C1`, `C2`
- minimum required signal per section/level: at least 2 terms, 1 expression, 1 sentence pattern
- current weak count: `0`

Important fixes from this audit:

- Introduction now returns recurrent-model terms instead of empty term output.
- Scaled dot-product attention now returns Q/K/V, dot products, softmax, and scaling language.
- Training/result/ablation sections now return setup/result language instead of generic fallback.
- Incidental prior model names and hardware names are de-prioritized for advanced levels.

### Eval Paper PDFs

These were checked from the real PDF files under `tmp/eval_papers`, not from hand-written snippets.

| Paper | Raw PDF pages | Learning sections | Pages without study sections | Extraction flags | Weak outputs |
| --- | ---: | ---: | --- | ---: | ---: |
| `attention_is_all_you_need.pdf` | 15 | 26 | 1, 11, 12 | 3 | 0 |
| `batch_norm.pdf` | 11 | 34 | none | 0 | 0 |
| `bert.pdf` | 16 | 45 | 10 | 1 | 0 |

Audit rule:

- every extracted learning section is checked at `B1`, `B2`, `C1`, and `C2`
- each section/level must produce at least 2 terms, 1 academic expression, and 1 sentence pattern
- all terms and expressions must be source-grounded

Interpretation of remaining page/flag notes:

- Attention pages 1, 11, and 12 are title/front-matter or references/non-learning material after filtering.
- BERT page 10 is references/non-learning material after filtering.
- Remaining Attention figure/table-leading flags are table/figure reading sections that still produce learning output, not empty section failures.
- BERT has one very short ablation-heading section, but it now produces valid learning signal.

### Source-Type Matrix

Representative source snippets are covered by automated tests for:

- ML paper
- medical paper
- climate report
- economics report
- API documentation
- video transcript

Each is checked across the learner levels where relevant. The goal is not just non-empty output; tests assert that the selected terms and expressions are the right kind of learning object for that source.

### YouTube URLs

YouTube native caption endpoints were rate-limited from this environment, so the URL audit now checks two paths:

- primary path: YouTube transcript APIs / yt-dlp caption tracks
- resilience path: known public transcript/article pages for curated demo URLs

Native caption URLs previously checked:

- ML explainer: `https://www.youtube.com/watch?v=eMlx5fFNoYc`
- climate explainer: `https://www.youtube.com/watch?v=G4H1N_yXBiA`
- economics explainer: `https://www.youtube.com/watch?v=3ez10ADR_gM`
- medical explainer: `https://www.youtube.com/watch?v=0h5Jd7sgQWY`
- FastAPI tutorial: `https://www.youtube.com/watch?v=7t2alSnE2-I`

Current live fetch result:

- all five failed with `502` from the transcript fetch path in this environment
- yt-dlp can currently read video metadata and caption track URLs for at least the ML URL
- direct YouTube timedtext caption URL fetch returns `429 Too Many Requests`
- root issue: YouTube caption/transcript access is unstable and can hit API/runtime/rate-limit problems

Mitigation added:

- transcript cache directory: `tmp/transcript_cache`
- successful transcript fetches are cached
- if a later live fetch fails, GemmaLens can reuse the stale cached transcript instead of losing the user workflow
- curated URL fallback is available for useful demo sources:
  - ML: `eMlx5fFNoYc` -> official 3Blue1Brown lesson text
  - climate: `9PFhrpyWV-w` -> Nerdfighteria transcript
  - economics: `3ez10ADR_gM` -> Nerdfighteria transcript
  - medical: `cUP8bGWln6M` -> Nerdfighteria transcript
  - FastAPI: `7t2alSnE2-I` -> public transcript/article page

Actual fallback result check:

| Source | URL | Fallback text chars | Segment count | B1/B2/C1/C2 weak outputs |
| --- | --- | ---: | ---: | ---: |
| ML explainer | `https://www.youtube.com/watch?v=eMlx5fFNoYc` | `33135` | `112` | `0` |
| Climate explainer | `https://www.youtube.com/watch?v=9PFhrpyWV-w` | `11967` | `40` | `0` |
| Economics explainer | `https://www.youtube.com/watch?v=3ez10ADR_gM` | `15098` | `49` | `0` |
| Medical explainer | `https://www.youtube.com/watch?v=cUP8bGWln6M` | `12371` | `43` | `0` |
| FastAPI tutorial | `https://www.youtube.com/watch?v=7t2alSnE2-I` | `42156` | `8` | `0` |

Weakness found and fixed during actual URL audit:

- climate opening returned only one term before adding climate-source terms such as `climate change`, `carbon dioxide`, `greenhouse gases`, and `atmospheric heating`
- economics opening returned only `economics` before adding source-grounded introductory-economics terms such as `theories and graphs` and `real world applications`
- FastAPI opening returned generic `key` before adding `FastAPI`, `APIs with Python`, `web framework`, `Python package manager`, and `pip`
- ML fallback contained an incidental `carbon dioxide` example; climate-only term promotion now requires climate context

Remaining weakness:

- arbitrary YouTube URLs can still fail when there is no cached transcript and no known public transcript/source page
- this should be explained in the UI as source availability, not analysis failure
- for the hackathon demo, use curated URLs with verified transcript fallback rather than depending on YouTube timedtext availability

## Verification Commands

Backend:

```bash
rtk backend/.venv-mlx/bin/python -m pytest backend/tests
```

Frontend:

```bash
cd frontend
rtk npm run build
```

Actual PDF section-level audit:

```bash
DATABASE_URL=sqlite:////Users/jaeman/Codes/GemmaLens/backend/gemmalens.db PYTHONPATH=backend rtk proxy backend/.venv-mlx/bin/python - <<'PY'
from app.db.session import SessionLocal
from app.models.document import Document
from app.services.document_section_service import DocumentSectionService
from app.services.analysis_normalization_service import AnalysisNormalizationService

session = SessionLocal()
doc = session.query(Document).filter(Document.title.ilike('%Attention%')).first()
sections = DocumentSectionService().split_with_labels(doc.content)
normalizer = AnalysisNormalizationService()
weak = []
for i, section in enumerate(sections, 1):
    for level in ["B1", "B2", "C1", "C2"]:
        data = normalizer.normalize_payload({}, "audit", section.text, support_language="Korean", target_level=level).model_dump()
        if len(data["terms"]) < 2 or len(data["phrases"]) < 1 or len(data["sentences"]) < 1:
            weak.append((i, section.title, level, len(data["terms"]), len(data["phrases"]), len(data["sentences"])))
print("sections", len(sections), "weak", len(weak))
print(weak)
PY
```

Eval paper audit is also covered by:

```bash
rtk backend/.venv-mlx/bin/python -m pytest backend/tests/test_learning_output_matrix.py
```

The test `test_eval_papers_all_extracted_sections_have_learning_signal_at_all_levels` reads the three real PDFs, extracts pages, splits sections, and checks every section at all four learner levels.
