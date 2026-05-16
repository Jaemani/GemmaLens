"use client";

import { BookOpenCheck, Clock, FileText, Link as LinkIcon, Play } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { AnalysisResult, TranscriptResponse, TranscriptSegment } from "@/lib/types";
import { AnalysisProgress } from "@/components/analysis/AnalysisProgress";

declare global {
  interface Window {
    YT?: {
      Player: new (elementId: string, options: Record<string, unknown>) => YouTubePlayer;
    };
    onYouTubeIframeAPIReady?: () => void;
  }
}

type YouTubePlayer = {
  getCurrentTime?: () => number;
  seekTo?: (seconds: number, allowSeekAhead: boolean) => void;
  destroy?: () => void;
};

export function VideoLearningPanel() {
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [videoId, setVideoId] = useState<string | null>(null);
  const [subtitleText, setSubtitleText] = useState("");
  const [sourceName, setSourceName] = useState("subtitle.srt");
  const [transcript, setTranscript] = useState<TranscriptResponse | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [busyLabel, setBusyLabel] = useState<string | null>(null);
  const [analysisElapsed, setAnalysisElapsed] = useState(0);
  const [analysisStep, setAnalysisStep] = useState(0);
  const [analysisLabel, setAnalysisLabel] = useState<string | null>(null);
  const [videoAnalysis, setVideoAnalysis] = useState<AnalysisResult | null>(null);
  const [videoAnalysisTitle, setVideoAnalysisTitle] = useState("");
  const [showSubtitleFallback, setShowSubtitleFallback] = useState(false);
  const playerRef = useRef<YouTubePlayer | null>(null);
  const playerElementId = "youtube-learning-player";
  const isAnalyzing = analysisLabel !== null;

  const activeSegment = useMemo(
    () => transcript?.segments.find((segment) => currentTime >= segment.start && currentTime < segment.end),
    [currentTime, transcript]
  );
  const pastedVideoId = useMemo(() => extractYouTubeId(youtubeUrl), [youtubeUrl]);
  const sceneText = useMemo(() => {
    if (!transcript || !activeSegment) return "";
    const startIndex = Math.max(0, activeSegment.index - 2);
    const endIndex = activeSegment.index + 1;
    return transcript.segments
      .filter((segment) => segment.index >= startIndex && segment.index <= endIndex)
      .map((segment) => segment.text)
      .join("\n");
  }, [activeSegment, transcript]);

  useEffect(() => {
    if (!videoId) return;
    let cancelled = false;

    function createPlayer() {
      if (cancelled || !window.YT) return;
      playerRef.current?.destroy?.();
      playerRef.current = new window.YT.Player(playerElementId, {
        videoId,
        playerVars: { modestbranding: 1, rel: 0 }
      });
    }

    if (window.YT) {
      createPlayer();
    } else {
      window.onYouTubeIframeAPIReady = createPlayer;
      const script = document.createElement("script");
      script.src = "https://www.youtube.com/iframe_api";
      document.body.appendChild(script);
    }

    const timer = window.setInterval(() => {
      const player = playerRef.current;
      if (typeof player?.getCurrentTime !== "function") return;
      setCurrentTime(player.getCurrentTime());
    }, 400);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
      playerRef.current?.destroy?.();
      playerRef.current = null;
    };
  }, [videoId]);

  useEffect(() => {
    if (!isAnalyzing) return;
    const timer = window.setInterval(() => {
      setAnalysisElapsed((value) => value + 1);
      setAnalysisStep((value) => Math.min(value + 1, 4));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [isAnalyzing]);

  async function parseSubtitle() {
    setBusy(true);
    setBusyLabel("Parsing pasted subtitles");
    setError(null);
    try {
      const result = await api.parseTranscript({ content: subtitleText, source_name: sourceName });
      setTranscript(result);
      if (!videoId) setVideoId(extractYouTubeId(youtubeUrl));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not parse subtitle.");
    } finally {
      setBusy(false);
      setBusyLabel(null);
    }
  }

  async function fetchYouTube() {
    const id = extractYouTubeId(youtubeUrl);
    if (!id) {
      setError("Paste a valid YouTube watch, short, embed, or youtu.be URL.");
      return;
    }
    setBusy(true);
    setBusyLabel("Fetching YouTube transcript");
    setError(null);
    try {
      setVideoId(id);
      setTranscript(null);
      const result = await api.fetchYouTubeTranscript({ url: youtubeUrl, languages: ["en", "ko"] });
      setTranscript(result);
      setSubtitleText("");
      setSourceName("subtitle.srt");
      if (result.source_id) setVideoId(result.source_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not fetch YouTube transcript.");
    } finally {
      setBusy(false);
      setBusyLabel(null);
    }
  }

  function seek(segment: TranscriptSegment) {
    playerRef.current?.seekTo?.(segment.start, true);
    setCurrentTime(segment.start);
  }

  async function analyzeTranscript() {
    if (!transcript?.plain_text.trim()) return;
    await analyzeText("Video transcript", transcript.plain_text, "transcript");
  }

  async function analyzeCurrentScene() {
    if (!sceneText.trim()) return;
    await analyzeText(`Video scene at ${formatTime(activeSegment?.start ?? currentTime)}`, sceneText, "video_segment");
  }

  async function analyzeText(title: string, content: string, sourceType: string) {
    setBusy(true);
    setBusyLabel(null);
    setAnalysisElapsed(0);
    setAnalysisStep(0);
    setAnalysisLabel(sourceType === "video_segment" ? "Creating current-scene learning source" : "Creating transcript learning source");
    setError(null);
    try {
      const document = await api.createDocument({ title, content, source_type: sourceType });
      setVideoAnalysisTitle(title);
      setAnalysisStep(1);
      setAnalysisLabel(sourceType === "video_segment" ? "Preparing nearby transcript lines" : "Preparing transcript chunks");
      const analysis = await api.analyzeDocument(document.id);
      setAnalysisStep(4);
      setAnalysisLabel(null);
      setVideoAnalysis(analysis);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not analyze transcript text.");
      setAnalysisLabel(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
      <section className="space-y-5">
        <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
          <h1 className="text-2xl font-semibold">Video learning</h1>
          <p className="mt-2 text-sm leading-6 text-neutral-600">
            Fetch a YouTube transcript, or paste subtitle text manually when YouTube captions are unavailable.
          </p>
          <div className="mt-5 grid gap-3 md:grid-cols-[1fr_auto]">
            <input
              value={youtubeUrl}
              onChange={(event) => setYoutubeUrl(event.target.value)}
              placeholder="YouTube URL"
              className="rounded-md border border-line px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={fetchYouTube}
              disabled={busy || !youtubeUrl.trim()}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {busyLabel === "Fetching YouTube transcript" ? <Clock size={16} className="animate-spin" /> : <LinkIcon size={16} />}
              {busyLabel === "Fetching YouTube transcript" ? "Fetching..." : "Fetch transcript"}
            </button>
          </div>
          {busyLabel ? (
            <p className="mt-3 rounded-md bg-blue-50 px-3 py-2 text-sm font-medium text-accent">{busyLabel}. This depends on caption availability and local network access.</p>
          ) : null}
          {youtubeUrl.trim() && !pastedVideoId ? (
            <p className="mt-2 text-xs text-amber-700">This does not look like a supported YouTube URL yet.</p>
          ) : null}
        </div>

        <div className="aspect-video overflow-hidden rounded-lg border border-line bg-black shadow-material">
          {videoId ? <div key={videoId} id={playerElementId} className="h-full w-full" /> : <EmptyPlayer />}
        </div>

        {!transcript ? (
          <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
            <button
              type="button"
              onClick={() => setShowSubtitleFallback((value) => !value)}
              className="inline-flex items-center gap-2 rounded-md border border-line px-4 py-2 text-sm font-semibold text-ink hover:bg-surface"
            >
              <FileText size={16} className="text-accent" />
              {showSubtitleFallback ? "Hide manual subtitles" : "Captions unavailable? Paste subtitles"}
            </button>
            {showSubtitleFallback ? (
              <>
                <input
                  value={sourceName}
                  onChange={(event) => setSourceName(event.target.value)}
                  className="mt-3 w-full rounded-md border border-line px-3 py-2 text-sm"
                  placeholder="subtitle filename"
                />
                <textarea
                  value={subtitleText}
                  onChange={(event) => setSubtitleText(event.target.value)}
                  rows={9}
                  className="mt-3 w-full resize-y rounded-md border border-line px-3 py-2 text-sm leading-6"
                  placeholder="Paste .srt or .vtt subtitle text."
                />
                <div className="mt-3 flex justify-end">
                  <button
                    type="button"
                    onClick={parseSubtitle}
                    disabled={busy || !subtitleText.trim()}
                    className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                  >
                    {busyLabel === "Parsing pasted subtitles" ? "Parsing..." : "Parse subtitle"}
                  </button>
                </div>
              </>
            ) : null}
            {error ? <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">{error}</p> : null}
          </div>
        ) : (
          <div className="rounded-lg border border-line bg-panel p-4 shadow-material">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm font-semibold">Transcript ready</p>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={analyzeCurrentScene}
                  disabled={busy || !sceneText.trim()}
                  className="inline-flex items-center gap-2 rounded-md border border-line px-4 py-2 text-sm font-semibold text-ink hover:bg-surface disabled:opacity-50"
                >
                  <BookOpenCheck size={16} />
                  Analyze current scene
                </button>
                <button
                  type="button"
                  onClick={analyzeTranscript}
                  disabled={busy || !transcript.plain_text.trim()}
                  className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                >
                  <BookOpenCheck size={16} />
                  Analyze transcript
                </button>
              </div>
            </div>
            {isAnalyzing ? (
              <div className="mt-4">
                <AnalysisProgress
                  title="Analyzing video transcript"
                  elapsed={analysisElapsed}
                  step={analysisStep}
                  currentLabel={analysisLabel}
                  labels={[
                    "Creating transcript source",
                    "Preparing transcript chunks",
                    "Running model analysis",
                    "Validating learning objects",
                    "Opening result"
                  ]}
                  hint="Keep watching. The lesson will appear here beside the video instead of opening a separate document page."
                />
              </div>
            ) : null}
            {error ? <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">{error}</p> : null}
          </div>
        )}
        {videoAnalysis ? <VideoInlineLesson analysis={videoAnalysis} title={videoAnalysisTitle} /> : null}
      </section>

      <aside className="rounded-lg border border-line bg-panel shadow-material">
        <div className="border-b border-line p-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-semibold">Transcript</h2>
            <span className="inline-flex items-center gap-1 rounded-full bg-surface px-2.5 py-1 text-xs font-semibold text-neutral-600">
              <Clock size={13} />
              {formatTime(currentTime)}
            </span>
          </div>
          {transcript?.warning ? <p className="mt-2 text-xs text-amber-700">{transcript.warning}</p> : null}
        </div>
        <div className="max-h-[720px] overflow-y-auto p-2">
          {transcript ? (
            transcript.segments.map((segment) => (
              <button
                key={segment.index}
                type="button"
                onClick={() => seek(segment)}
                className={`w-full rounded-md p-3 text-left text-sm leading-6 transition ${
                  activeSegment?.index === segment.index ? "bg-blue-50 text-ink" : "hover:bg-surface"
                }`}
              >
                <span className="mb-1 block text-xs font-semibold text-accent">{formatTime(segment.start)}</span>
                {segment.text}
              </button>
            ))
          ) : (
            <div className="space-y-3 p-4 text-sm leading-6 text-neutral-600">
              <p className="font-semibold text-ink">No transcript loaded</p>
              <p>Load captions to turn timeline segments into language lessons. You can analyze the full transcript or only the current scene.</p>
              <div className="rounded-md bg-surface p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Learning flow</p>
                <ol className="mt-2 space-y-1">
                  <li>1. Fetch YouTube captions or paste subtitles.</li>
                  <li>2. Click a timestamp to sync the scene.</li>
                  <li>3. Analyze one scene or the whole transcript.</li>
                </ol>
              </div>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}

function VideoInlineLesson({ analysis, title }: { analysis: AnalysisResult; title: string }) {
  const concepts = (analysis.concepts ?? []).slice(0, 4);
  const terms = analysis.terms.slice(0, 6);
  const phrases = analysis.phrases.slice(0, 5);
  const sentence = analysis.sentences[0];

  return (
    <section className="rounded-lg border border-line bg-panel shadow-material">
      <div className="border-b border-line p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Video lesson</p>
        <h2 className="mt-1 text-lg font-semibold">{title || "Current video lesson"}</h2>
        <p className="mt-2 text-sm leading-6 text-neutral-700">{analysis.summaries.one_line}</p>
      </div>
      <div className="grid gap-4 p-5">
        <div className="rounded-md border border-line bg-surface p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Watch for</p>
          <p className="mt-2 text-sm leading-6 text-neutral-700">{analysis.summaries.simple}</p>
          {analysis.summaries.study_notes.length ? (
            <ul className="mt-3 space-y-2">
              {analysis.summaries.study_notes.slice(0, 3).map((note) => (
                <li key={note} className="text-sm leading-6 text-neutral-700">
                  <span className="mr-2 font-semibold text-accent">Focus</span>
                  {note}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        {concepts.length ? (
          <CompactVideoList
            title="Ideas in this scene"
            rows={concepts.map((concept) => ({
              text: concept.concept,
              meaning: concept.explanation || concept.why_it_matters,
              source: concept.source_sentence
            }))}
          />
        ) : null}
        <CompactVideoList
          title="Words to listen for"
          rows={terms.map((term) => ({ text: term.term, meaning: term.meaning, source: term.source_sentence }))}
        />
        <CompactVideoList
          title="Useful spoken expressions"
          rows={phrases.map((phrase) => ({ text: phrase.phrase, meaning: phrase.explanation, source: phrase.source_sentence }))}
        />
        {sentence ? (
          <div className="rounded-md border border-line bg-surface p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Sentence pattern</p>
            <p className="mt-2 text-sm font-semibold text-ink">{sentence.core_structure}</p>
            <p className="mt-2 text-sm leading-6 text-neutral-700">{sentence.korean_explanation || sentence.simplified_version}</p>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function CompactVideoList({ title, rows }: { title: string; rows: Array<{ text: string; meaning: string; source?: string }> }) {
  if (!rows.length) return null;
  return (
    <div className="rounded-md border border-line bg-surface p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{title}</p>
      <div className="mt-3 grid gap-3">
        {rows.map((row) => (
          <div key={`${title}:${row.text}`} className="border-t border-line pt-3 first:border-t-0 first:pt-0">
            <p className="text-sm font-semibold text-ink">{row.text}</p>
            <p className="mt-1 text-sm leading-6 text-neutral-700">{row.meaning}</p>
            {row.source ? <p className="mt-1 text-xs leading-5 text-neutral-500">{truncate(row.source, 180)}</p> : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function truncate(value: string, limit: number) {
  const normalized = value.split(/\s+/).join(" ").trim();
  if (normalized.length <= limit) return normalized;
  return `${normalized.slice(0, limit).trim()}...`;
}

function EmptyPlayer() {
  return (
    <div className="flex h-full items-center justify-center text-sm font-semibold text-white">
      <div className="px-6 text-center">
        <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-white/10">
          <Play size={18} />
        </div>
        <p className="mt-3">Add a YouTube URL to load the player</p>
        <p className="mt-1 text-xs font-medium text-white/70">Captions become timestamped learning segments.</p>
      </div>
    </div>
  );
}

function extractYouTubeId(url: string) {
  try {
    const parsed = new URL(url);
    if (parsed.hostname.includes("youtu.be")) return parsed.pathname.replace("/", "") || null;
    if (parsed.pathname === "/watch") return parsed.searchParams.get("v");
    if (parsed.pathname.startsWith("/embed/") || parsed.pathname.startsWith("/shorts/")) return parsed.pathname.split("/")[2] ?? null;
  } catch {
    return null;
  }
  return null;
}

function formatTime(seconds: number) {
  const total = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return `${minutes}:${rest.toString().padStart(2, "0")}`;
}
