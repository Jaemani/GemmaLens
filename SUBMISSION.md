# GemmaLens - Gemma 4 Good Submission

## Links

- Live demo: TBD
- Public video: TBD
- Kaggle writeup: see `docs/KAGGLE_WRITEUP_DRAFT.md`
- Public repository: this repository

## Positioning

GemmaLens is a local-first academic reading coach for non-native learners.
It keeps the source visible and turns papers, reports, technical documents, and
subtitle transcripts into source-grounded learning objects.

Primary track: Future of Education.

Secondary framing:

- Digital Equity & Inclusivity: reduces academic-English barriers for students
  and researchers.
- Safety & Trust: local/private processing is part of the product premise.

## Demo Sources

Primary document demo:

- `Attention Is All You Need`

Recommended showmanship/history set:

- AlphaFold 3 biomolecular interactions
- IMF World Economic Outlook 2025
- IPCC AR6 Synthesis Report
- Pew Teens, Social Media and Technology 2024
- Global inequalities in clinical trials participation
- DeepSeek-R1
- UI-TARS

Local demo PDFs should stay outside the repository. Current local folder:

```txt
~/Documents/GemmaLensDemoPapers
```

## What To Avoid In Submission

- Do not claim native video/audio understanding. Current video learning is
  transcript/subtitle-based.
- Do not claim perfect privacy, complete compliance, or production readiness.
- Do not commit downloaded videos, private subtitles, model weights, local
  runtime config, SQLite databases, or private transcripts.
- Do not make The Thinking Game the core rights-clear local-video proof. Treat
  it as optional online transcript demonstration only.

## Supporting Docs

- Architecture and technical report: `docs/TECHNICAL_REPORT.md`
- Deployment and judging backend setup: `docs/DEPLOYMENT.md`
- Final draft pack: `docs/KAGGLE_WRITEUP_DRAFT.md`
- Video learning strategy: `docs/VIDEO_LEARNING_STRATEGY.md`
- Recent product changes: `docs/RECENT_PRODUCT_CHANGELOG.md`

## Final Checks

Before public push:

```bash
rg -n "api[_-]?key|secret|token|tailscale|100\\.|/Users/|YTS|The Thinking Game" .
npm --prefix frontend run build
git diff --check
```
