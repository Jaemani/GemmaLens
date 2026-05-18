# GemmaLens Gemma 4 Good Final Submission Draft Pack

Date: 2026-05-18
Purpose: final working draft package for Kaggle writeup, public video, repository, demo, and media choices.

## 0. Non-Submission Notes

Do not paste this section into Kaggle. It is not part of the 1,500-word writeup.

### A/B/C Synthesis

- **Agent C was adopted for story.** It had the best judge-facing opening: a concrete non-native graduate student, the "reading coach, not reading replacement" framing, and the "Read the paper. Build the skill." tagline.
- **Agent A was adopted for evidence.** It had the safest full structure, repo strategy, quality-evaluation evidence, and limitations.
- **Agent B was mined for sharp contrast only.** Keep "disposable translation" and "academic self-reliance"; reject perfect/complete/production-ready/ultra-low-latency claims.

### Final Editorial Rule

```txt
Agent C opening + Agent A evidence + Agent B differentiation - all absolute claims = final submission direction.
```

### Must Not Claim

- No native video/audio understanding. Current video mode is subtitle/transcript-based.
- No perfect privacy or complete compliance.
- No mature spaced-repetition system.
- No E4B superiority. Current evaluation did not show clear aggregate advantage over E2B.
- No "any PDF" or "any language" perfection.
- No copyright-safe claim for The Thinking Game downloads/subtitles.

### Current Addition

The 2026-05-19 revision adds a stronger "why Gemma 4" story without turning it into an overclaim:

- Gemma 4 E-series made local-first reading feel viable.
- Edge-class models matter because the product uses small staged learning jobs.
- Translation/general academic knowledge is already strong enough for useful learning support.
- A ThinkPad AMD Ryzen 5 5500U anecdote supports the edge-device story.
- Offline translation was surprisingly strong in best warm-model conditions, but latency variance and runtime control limits remain honest caveats.

## 1. Kaggle Writeup Draft - English

Target: under 1,500 words.
Suggested track: Future of Education.
Secondary framing: Digital Equity & Inclusivity, Safety & Trust.

### Title

GemmaLens: Read the Paper. Build the Skill.

### Draft

A graduate student opens a dense paper late at night. Their English is good enough to translate sentences, but not fast enough to read the whole paper with confidence. A translator makes one sentence clear. The next sentence is still hard.

That is the gap GemmaLens addresses. Translation helps once. GemmaLens helps you read the next one.

I am also that student. I'm a Korean undergraduate, and reading English papers is part of my week. I built GemmaLens because the tools I was using were not making me a better reader. They were just making the current paragraph less painful.

GemmaLens is a local-first academic reading coach for non-native learners. It turns papers, technical documents, and subtitle transcripts into source-grounded learning objects: key ideas, technical vocabulary, reusable academic phrases, sentence patterns, and review items. The goal is not to replace reading with a summary or a chat answer. The goal is to keep the original source visible and help the learner actually build their academic English while reading real material.

Most AI reading tools fall into one of four patterns: translation, summarization, chat, or document search. GemmaLens is different. A translator gives you a disposable sentence. A summarizer hides the source. A chatbot is unstructured. A PDF RAG app answers questions about a document but does not teach you to read it.

There are excellent AI tools built on SOTA models — summarizers, question generators, answer engines — and they are useful for some tasks. But none of them made me a better reader. If I read a summary, I cannot tell what I missed. The next paper still feels just as hard. Same with technical videos and lectures: I get a recap, but I cannot watch the next one any better on my own. That is the gap GemmaLens closes. The paper stays primary, and Gemma 4 produces the scaffolding around it.

Gemma 4 is at the center of this project. Honestly, it is the reason the project exists in the form it does.

I started this skeptical of local models. A year ago, if I had tried to build a learning coach on a 2B or 4B open model, I am pretty sure the result would have been a demo, not a tool. Translation would have drifted. Technical terms would have come back as approximations. Structured output would have broken half the time. That was the honest state of small open models, and it is why most useful AI tools were still cloud products.

The Gemma 4 E-series surprised me. For the specific things a learning coach has to do — translating an academic sentence into Korean without losing the meaning, explaining how a phrase like 'we show that' actually works in a paper, writing a glossary entry for a technical term, pulling out reusable sentence patterns — the output was good enough to actually use. Not "interesting for a demo" good. Actually useful, on a laptop, without a network connection. These are exactly the things an undergraduate or a graduate student needs every day.

I want to be clear about the scope. SOTA models still have a long way to go on hard reasoning and agentic tasks. I am not claiming Gemma 4 closes that gap. What I am saying is that the floor of what edge models can do has moved up enough that a single developer on consumer hardware can now build things that needed cloud infrastructure twelve months ago.

The moment this really hit me was not on my Mac. It was on a ThinkPad with an AMD Ryzen 5 5500U — a chip designed for writing documents, not running language models. I expected the remote-Gemma-over-Tailscale setup to be a slideshow at best. It was not. The learning objects coming back were clean, and the latency stopped being the bottleneck — the output quality became what I was paying attention to. A laptop with no discrete GPU, running a small open model, was producing the kind of material my project is built around. That was when I stopped designing GemmaLens as "a cloud product with a local fallback" and started designing it as a local-first product where cloud is the fallback.

The same shift came from a smaller feature I almost did not bother with. When I read papers in English, I switch into Korean constantly to check whether I actually understood a phrase, then go back to the source. So I added an offline translation path, more as a quiet utility than a headline feature. What I did not expect was how good it would be. Gemma 4 covered hundreds of languages and ran without a network. In the best case, with the model warm, it translated a full paragraph in under three seconds on a regular consumer laptop. I have not figured out how to hit that ceiling on every call yet — the variance is real and the engineering is still my homework. But the ceiling exists, and it is genuinely surprising. Multilingual paragraph translation, fully offline, in three seconds, on a machine someone already owns — that was a cloud capability a year ago. Watching it happen locally was the second moment in this project that changed how I think about what edge models can carry.

Two properties of Gemma 4 shaped GemmaLens in concrete ways. Its speed on edge devices made "first page first" a real workflow instead of a loading screen — a learner sees a usable lesson in seconds, not minutes. Its structured output behavior made the learning-object schema (terms, phrases, concepts, patterns, summaries, source evidence) a stable contract between the model and the UI, instead of something that breaks every other run.

The runtime ecosystem matters too. Gemma 4 runs mature enough that the same architecture can move from my Mac to my ThinkPad and, technically on the mobile phone.

I am submitting this project because building it gave me real conviction about where local language models are heading. The E-series did not just pass a benchmark. It was fast enough, accurate enough, and structured enough that a single student on consumer hardware could build something that needed cloud infrastructure a year ago.

On the technical side, GemmaLens is a Next.js frontend and a FastAPI backend with SQLite storage, behind a provider-neutral model adapter layer. The backend supports a mock adapter for UI testing, an MLX/llama.cpp route, and a remote/private Gemma route. The public demo runs as a Vercel frontend proxying through a private backend tunnel to a local FastAPI/Gemma runtime, so browser clients never receive private backend keys. For long PDFs, the source appears next to a paper map that grows as sections are analyzed, instead of pretending the whole paper is understood from the start.

GemmaLens also supports local or online video learning through subtitle/transcript. This is intentionally subtitle-based today, not direct video or audio understanding. That keeps the demo honest and respects media rights, while still letting a learner study local video and subtitle files they have the right to use.

I built an evaluation harness because a learning tool should not only look good in screenshots; it should expose its own failure modes. I ran a 36-run quality matrix across Gemma 4 E2B and E4B, multiple sources, learner levels, and support-language settings. Sources included Attention Is All You Need, Batch Normalization, Convex Optimization, and two technical video transcripts. Levels covered B1 through C2 and a domain-heavy setting. Korean was the full support-language matrix; I did smoke tests in English. I ran the Korean matrix in full because I am a native Korean speaker, and I can actually judge whether the Korean output is good. I did not feel qualified to grade output in a language I do not speak fluently.

The pre-fix mean heuristic score was 3.74 out of 5, with no fallback-marker runs. E2B averaged 57.1 seconds and E4B averaged 104.3 seconds, and E4B was not clearly better in this matrix. That result mattered: it pushed me toward staged, progressive analysis instead of assuming a larger model would just be better.

The evaluation also surfaced real problems. Some outputs leaked the wrong support language. Some video outputs used paper-style wording. Some phrases came out weak or not reusable. GemmaLens now enforces source-type-aware normalization, support-language validation, and weak-expression filtering. The backend test suite passes 152 tests, Ruff checks pass on the touched files, and the frontend TypeScript check passes.

GemmaLens belongs primarily in Future of Education — building reading skill instead of substituting for it. The local-first design extends that into Digital Equity for learners who cannot afford cloud budgets, and Safety & Trust for anyone reading unpublished or licensed material.

The system has limits. Scanned PDFs need OCR. Video learning is transcript-based. The review loop is early. Local latency can be visible. I am including these limits in the submission because the project is built on honest, source-grounded learning, not on broad claims.

GemmaLens is not trying to read the paper for the learner. It is trying to make the learner stronger at reading the next one.

## 3. Public Video Plan

Target length: 2:45-2:55. Do not use the full 3 minutes unless necessary.

### Public Video Principle

This should not be a feature tour. It should prove one idea:

> GemmaLens keeps the source visible and uses Gemma 4 to turn it into durable learning objects.

### Edited Version

| Time | Screen | Voiceover / Action |
| --- | --- | --- |
| 0:00-0:12 | Dense academic paper, one difficult sentence highlighted | "Translation helps once. It does not teach the next paper." |
| 0:12-0:25 | GemmaLens dashboard / document workspace | "GemmaLens is a local-first Gemma 4 reading coach for non-native learners." |
| 0:25-0:45 | Open/upload a PDF or prepared sample | Cut delay. Show source-aware workspace opening. |
| 0:45-1:10 | Source left, learning objects right | Show one term, one academic phrase, one sentence pattern, and source evidence. |
| 1:10-1:25 | Save one phrase and one concept | "Useful academic language becomes reviewable memory." |
| 1:25-1:45 | Progressive paper map | "The map grows from analyzed sections. GemmaLens does not pretend the whole paper is understood before analysis finishes." |
| 1:45-2:10 | Local video/subtitle workflow | Use rights-clear local video and local `.srt`/transcript. Show one timed subtitle line and generated expression/term. |
| 2:10-2:35 | Simple architecture diagram | "Gemma 4's local-friendly models shaped staged analysis, caching, validation, and source evidence." |
| 2:35-2:55 | Final title card | "Read the paper. Build the skill." |

### Honest Live-Recording Version

Use if visible latency remains:

- Warm the model before recording.
- Show one real analysis action.
- If waiting appears, narrate:

> "This is local/private edge analysis. GemmaLens prepares sections and shows useful work as soon as it can instead of pretending the whole paper is instantly understood."

- Then move to cached/ready sections.
- Do not live-fetch YouTube captions during the public video.
- Do not show terminal logs, private URLs, local IPs, Tailscale hostnames, or API keys.

### Public Video: What Not To Show

- Do not show The Thinking Game as downloaded local media.
- Do not show YTS or downloaded movie-subtitle source strings.
- Do not show wrong-language output.
- Do not show raw model/debug panels.
- Do not show "production-ready", "perfect privacy", or "native video understanding" claims.
- Do not spend the final 30 seconds scrolling quality-eval docs. Use one clean architecture/impact close.

## 4. Demo Media Plan

### Local Downloaded Video - Recommended Primary Choice

Use **Tears of Steel** for the local downloaded video demo.

Why:

- It is a Blender Foundation open movie.
- It is available for official download.
- It is licensed under **Creative Commons Attribution 3.0 (CC BY 3.0)**.
- It has subtitle files available through Wikimedia timed text.
- It demonstrates the "local video + local subtitles" workflow without relying on YouTube transcript APIs.
- It is widely known in the open-source / computer graphics / Blender community, so it is still tech-adjacent even though it is a sci-fi short film rather than an AI lecture.

Use it as:

- local video source
- local English subtitle source
- optional Korean subtitle if available or generated separately for internal demo

Attribution text:

```txt
"Tears of Steel" by Blender Foundation / Project Mango, licensed under CC BY 3.0.
Source: <https://mango.blender.org/download/>
License: <https://creativecommons.org/licenses/by/3.0/>
```

Official sources:

- Download page: https://mango.blender.org/download/
- Creative Commons page: https://wiki.creativecommons.org/wiki/Tears_of_Steel
- Wikimedia video/subtitles: https://commons.wikimedia.org/wiki/File:Tears_of_Steel_in_4k_-_Official_Blender_Foundation_release.webm
- English subtitle: https://commons.wikimedia.org/wiki/TimedText:Tears_of_Steel_in_4k_-_Official_Blender_Foundation_release.webm.en.srt

### Tech Lecture Alternative

Use **MIT OpenCourseWare 6.7960 Deep Learning - Lec 08. Architectures: Transformers** if you want a more directly AI/Transformer-themed local video.

Why:

- It is directly related to transformers.
- MIT OCW provides a download video link and transcript.
- MIT OCW materials are generally under **CC BY-NC-SA** unless otherwise marked.

Caution:

- CC BY-NC-SA is not the same as unrestricted commercial reuse.
- Use only with attribution and license link.
- Do not bundle it into the repo.
- If the public-submission/prize context feels legally ambiguous, use Tears of Steel or a self-created video instead.

Attribution text:

```txt
MIT OpenCourseWare, 6.7960 Deep Learning, Fall 2024, Lec 08. Architectures: Transformers.
Licensed by MIT OCW under CC BY-NC-SA unless otherwise marked.
Source: <https://ocw.mit.edu/courses/6-7960-deep-learning-fall-2024/resources/mit6_7960f24_lec08_mp4/>
```

Official sources:

- Lecture page: https://ocw.mit.edu/courses/6-7960-deep-learning-fall-2024/resources/mit6_7960f24_lec08_mp4/
- Lecture videos index: https://ocw.mit.edu/courses/6-7960-deep-learning-fall-2024/video_galleries/lecture-videos/
- OCW reuse/license FAQ: https://mitocw.zendesk.com/hc/en-us/articles/4414756181403-How-is-all-rights-reserved-content-different-from-the-rest-of-OCW-content/

### Online Demo Media

The user plans to show **The Thinking Game** for online mode.

Safe handling:

- Treat it as an online/external-source demo only.
- Do not download and bundle the video.
- Do not commit subtitles.
- Do not claim reuse/redistribution rights.
- Do not make it the core public video sample.
- If captions fail or rate limits appear, switch to a prepared rights-clear local subtitle demo.

Public copy:

```txt
Online transcript mode can work with public videos when captions are available, but the core local-video demo uses rights-clear local video/subtitle files.
```

## 5. Repository / Submission Checklist

### Add `SUBMISSION.md`

Recommended content:

```markdown
# GemmaLens - Gemma 4 Good Submission

- Live demo:
- Public video:
- Kaggle writeup:
- Architecture: docs/TECHNICAL_REPORT.md
- Quality evaluation: docs/QUALITY_EVAL_REPORT.md
- Deployment: docs/DEPLOYMENT.md
- Known limitations:
```

### Before Public Push

Run:

```bash
rg -n "api[_-]?key|secret|token|tailscale|100\\.|/Users/|YTS|The Thinking Game" .
```

Remove or exclude:

- `.env`
- private API keys
- private Tailscale hostnames / IPs
- local model weights
- downloaded videos
- downloaded movie subtitles
- `frontend/tsconfig.tsbuildinfo`
- `tmp.png`
- root `gemmalens_hero.png` if duplicated in `frontend/public/`
- root `gemmalens_icon/` if only source/export material

### Demo Stability Checklist

- Backend running and reachable.
- Vercel env:
  - `BACKEND_INTERNAL_URL`
  - `GEMMALENS_API_KEY`
- Browser does not expose backend API key.
- Model warmed before recording/demo.
- One document already cached and clean.
- One local video/subtitle sample ready.
- The Thinking Game online demo treated as optional.
- No UI text says `paper` for video transcript.
- No output shows fallback-language leakage.

## 6. Final Intent Check

The final package should communicate this flow:

```txt
Problem:
Non-native learners can translate sentences but still struggle to read academic material independently.

Solution:
GemmaLens keeps the source visible and turns it into source-grounded learning objects.

Why Gemma 4:
Small local/edge Gemma 4 models shaped staged analysis, caching, validation, and private learning.

Evidence:
36-run evaluation, guardrail fixes, backend/frontend checks.

Demo:
One paper + one rights-clear local subtitle video.

Honesty:
Transcript-based video, OCR limits, early review loop, local latency.
```

If any final writeup or video drifts toward "PDF summarizer", "translator", "chatbot", "perfect privacy", or "native video understanding", cut it.
