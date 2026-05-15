"use client";

import { BookOpenCheck, Clock, FileText, Link as LinkIcon, Play } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { TranscriptResponse, TranscriptSegment } from "@/lib/types";

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
  const router = useRouter();
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [videoId, setVideoId] = useState<string | null>(null);
  const [subtitleText, setSubtitleText] = useState("");
  const [sourceName, setSourceName] = useState("subtitle.srt");
  const [transcript, setTranscript] = useState<TranscriptResponse | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const playerRef = useRef<YouTubePlayer | null>(null);
  const playerElementId = "youtube-learning-player";

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

  async function parseSubtitle() {
    setBusy(true);
    setError(null);
    try {
      const result = await api.parseTranscript({ content: subtitleText, source_name: sourceName });
      setTranscript(result);
      if (!videoId) setVideoId(extractYouTubeId(youtubeUrl));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not parse subtitle.");
    } finally {
      setBusy(false);
    }
  }

  async function fetchYouTube() {
    const id = extractYouTubeId(youtubeUrl);
    if (!id) {
      setError("Paste a valid YouTube watch, short, embed, or youtu.be URL.");
      return;
    }
    setBusy(true);
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
    setError(null);
    try {
      const document = await api.createDocument({ title, content, source_type: sourceType });
      await api.analyzeDocument(document.id);
      router.push(`/analysis/${document.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not analyze transcript text.");
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
              <LinkIcon size={16} />
              Fetch transcript
            </button>
          </div>
          {youtubeUrl.trim() && !pastedVideoId ? (
            <p className="mt-2 text-xs text-amber-700">This does not look like a supported YouTube URL yet.</p>
          ) : null}
        </div>

        <div className="aspect-video overflow-hidden rounded-lg border border-line bg-black shadow-material">
          {videoId ? <div key={videoId} id={playerElementId} className="h-full w-full" /> : <EmptyPlayer />}
        </div>

        {!transcript ? (
          <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <FileText size={17} className="text-accent" />
            Subtitle fallback
          </div>
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
          />
          <div className="mt-3 flex flex-wrap justify-end gap-3">
            <button
              type="button"
              onClick={parseSubtitle}
              disabled={busy || !subtitleText.trim()}
              className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              Parse subtitle
            </button>
          </div>
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
            {error ? <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">{error}</p> : null}
          </div>
        )}
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
            <p className="p-4 text-sm text-neutral-600">Fetch a transcript or parse subtitles to start timeline learning.</p>
          )}
        </div>
      </aside>
    </div>
  );
}

function EmptyPlayer() {
  return (
    <div className="flex h-full items-center justify-center text-sm font-semibold text-white">
      <div className="flex items-center gap-2">
        <Play size={18} />
        Add a YouTube URL to load the player
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
