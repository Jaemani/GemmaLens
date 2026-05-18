# GemmaLens: A Local-First Academic Reading Coach

A graduate student opens a dense paper late at night. Their English is good enough to translate sentences, but not fast enough to read the whole paper with confidence. A translator makes one sentence clear. The next sentence is still hard.

That is the gap GemmaLens addresses. Translation helps once. GemmaLens helps you read the next one.

I am also that student. I am a Korean undergraduate, and reading English papers is part of my week. I built GemmaLens because the tools I was using were not making me a better reader. They were just making the current paragraph less painful.

GemmaLens is a local-first academic reading coach for non-native learners. It turns papers, technical documents, and subtitle transcripts into source-grounded learning objects: key ideas, technical vocabulary, reusable academic phrases, sentence patterns, and review items. The goal is not to replace reading with a summary or a chat answer. The goal is to keep the original source visible and help the learner build academic English while reading real material.

Most AI reading tools fall into one of four patterns: translation, summarization, chat, or document search. GemmaLens is different. A translator gives you a disposable sentence. A summarizer hides the source. A chatbot is unstructured. A PDF RAG app answers questions about a document but does not teach you to read it.

There are excellent AI tools built on SOTA models, and they are useful for many tasks. But none of them made me a better reader. If I read a summary, I cannot tell what I missed. The next paper still feels just as hard. The same is true for technical videos and lectures: I get a recap, but I cannot watch the next one any better on my own. GemmaLens keeps the paper primary, and Gemma 4 produces scaffolding around it.

## Why Gemma 4

Gemma 4 is at the center of this project. Honestly, it is the reason the project exists in the form it does.

I started this skeptical of local models. A year ago, if I had tried to build a learning coach on a 2B or 4B open model, I am pretty sure the result would have been a demo, not a tool. Translation would have drifted. Technical terms would have come back as approximations. Structured output would have broken under real schema pressure. That was the honest state of small open models, and it is why most useful AI tools were still cloud products.

The Gemma 4 E-series surprised me. For the specific things a learning coach has to do — translating an academic sentence into Korean without losing the meaning, explaining how a phrase like "we show that" works in a paper, writing a glossary entry for a technical term, and pulling out reusable sentence patterns — the output was good enough to actually use. Not just interesting for a demo. Actually useful, on a laptop, without a network connection. These are exactly the things an undergraduate or graduate student needs every day.

I want to be clear about the scope. SOTA models still have a long way to go on hard reasoning and agentic tasks. I am not claiming Gemma 4 closes that gap. What I am saying is that the floor of edge models has moved up enough that a single developer on consumer hardware can now build things that needed cloud infrastructure twelve months ago.

The moment this really hit me was not on my Mac. It was on a ThinkPad with an AMD Ryzen 5 5500U, a chip designed for writing documents, not running language models. I expected the remote-Gemma-over-Tailscale setup to be a slideshow. It was not. The learning objects coming back were clean, and the latency stopped being the bottleneck; the output quality became what I was paying attention to. A laptop with no discrete GPU, running a small open model, was producing the kind of material my project is built around. That was when I stopped designing GemmaLens as a cloud product with a local fallback and started designing it as a local-first product where cloud is the fallback.

The same shift came from a smaller feature I almost did not bother with. When I read papers in English, I switch into Korean constantly to check whether I actually understood a phrase, then go back to the source. So I added an offline translation path, more as a quiet utility than a headline feature. What I did not expect was how good it would be. Gemma 4 showed broad multilingual coverage and ran without a network. In the best case, with the model warm, it translated a full paragraph in under three seconds on a regular consumer laptop. I have not figured out how to hit that ceiling on every call yet; the variance is real and the engineering is still mine to do. But the ceiling exists, and it is genuinely surprising. Multilingual paragraph translation, fully offline, at conversational latency, on a machine someone already owns — that felt like a cloud-only workflow a year ago.

Two properties of Gemma 4 shaped GemmaLens directly. Its edge speed made "first page first" a real workflow instead of a loading screen: a learner sees a usable lesson in seconds, not minutes. Its structured output behavior made the learning-object schema — terms, phrases, concepts, patterns, summaries, source evidence — a stable contract between the model and the UI, instead of something that breaks every other run.

The runtime ecosystem matters too. The local ecosystem around Gemma 4 is mature enough that the same architecture can move from my Mac to my ThinkPad and toward mobile-class edge devices. I am submitting this project because building it gave me real conviction about where local language models are heading. The E-series did not just pass a benchmark. It was fast enough, accurate enough, and structured enough that a single student on consumer hardware could build something that needed cloud infrastructure a year ago.

## How It Works

GemmaLens is a Next.js frontend and FastAPI backend with SQLite storage, behind a provider-neutral model adapter layer. The backend supports a mock adapter for UI testing, an MLX/llama.cpp route, and a remote/private Gemma route. The public demo runs as a Vercel frontend proxying through a private backend tunnel to a local FastAPI/Gemma runtime, so browser clients never receive private backend keys. For long PDFs, the source appears next to a paper map that grows as sections are analyzed, instead of pretending the whole paper is understood from the start.

GemmaLens also supports local or online video learning through subtitles/transcripts. This is intentionally subtitle-based today, not direct video or audio understanding. That keeps the demo honest and respects media rights, while still letting a learner study local video and subtitle files they have the right to use.

## Evaluation

I treated evaluation as a product-design problem rather than a leaderboard. A reading coach fails when it shows fluent but ungrounded text, chooses vocabulary that is too easy or too random, leaks the wrong support language, or turns a video transcript into paper-style prose. GemmaLens is built to make those failures visible and recoverable: each learning object keeps source evidence, target level, support-language glosses, and a type label, so the UI can separate vocabulary, reusable phrases, concepts, and sentence patterns instead of presenting one undifferentiated summary.

That feedback loop shaped the implementation. Long documents are analyzed section by section instead of being treated as one instant whole-paper answer. The backend normalizes model output, filters weak expressions, preserves native-language explanations, and avoids filling empty sections with fake learning objects. For videos, the system stays honest: it teaches from subtitles and transcripts, not from native audio/video understanding. The goal is not to claim perfect automatic tutoring, but to keep the learner close to the source while reducing the common failure modes that make AI reading tools feel impressive but hard to trust.

## Impact and Limits

GemmaLens belongs primarily in Future of Education: building reading skill instead of substituting for it. The local-first design extends that into Digital Equity for learners who cannot afford cloud budgets, and Safety & Trust for anyone reading unpublished or licensed material.

The system has limits. Scanned PDFs need OCR. Video learning is transcript-based. The review loop is early. Local latency can be visible. I include these limits because the project is built on honest, source-grounded learning, not broad claims.

GemmaLens is not trying to read the paper for the learner. It is trying to make the learner stronger at reading the next one.
