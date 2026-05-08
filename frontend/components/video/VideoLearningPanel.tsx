"use client";

import { Clock, FileText, Link as LinkIcon, Play } from "lucide-react";
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
  getCurrentTime: () => number;
  seekTo: (seconds: number, allowSeekAhead: boolean) => void;
};

const SAMPLE_SRT = `1
00:00:01,000 --> 00:00:03,500
You're not gonna get away with this.

2
00:00:04,000 --> 00:00:06,200
I should have told you earlier.

3
00:00:07,000 --> 00:00:10,000
This changes everything.
`;

export function VideoLearningPanel() {
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [videoId, setVideoId] = useState<string | null>(null);
  const [subtitleText, setSubtitleText] = useState(SAMPLE_SRT);
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

  useEffect(() => {
    if (!videoId) return;
    let cancelled = false;

    function createPlayer() {
      if (cancelled || !window.YT) return;
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
      if (playerRef.current) setCurrentTime(playerRef.current.getCurrentTime());
    }, 400);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [videoId]);

  async function parseSubtitle() {
    setBusy(true);
    setError(null);
    try {
      const result = await api.parseTranscript({ content: subtitleText, source_name: "pasted-subtitle.srt" });
      setTranscript(result);
      if (!videoId) setVideoId(extractYouTubeId(youtubeUrl));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not parse subtitle.");
    } finally {
      setBusy(false);
    }
  }

  async function fetchYouTube() {
    setBusy(true);
    setError(null);
    try {
      const id = extractYouTubeId(youtubeUrl);
      setVideoId(id);
      const result = await api.fetchYouTubeTranscript({ url: youtubeUrl, languages: ["en", "ko"] });
      setTranscript(result);
      if (result.source_id) setVideoId(result.source_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not fetch YouTube transcript.");
    } finally {
      setBusy(false);
    }
  }

  function seek(segment: TranscriptSegment) {
    playerRef.current?.seekTo(segment.start, true);
    setCurrentTime(segment.start);
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
      <section className="space-y-5">
        <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
          <h1 className="text-2xl font-semibold">Video learning</h1>
          <p className="mt-2 text-sm leading-6 text-neutral-600">
            Start with subtitles or an experimental YouTube transcript. The player and transcript stay synced by timestamp.
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
        </div>

        <div className="aspect-video overflow-hidden rounded-lg border border-line bg-black shadow-material">
          {videoId ? <div id={playerElementId} className="h-full w-full" /> : <EmptyPlayer />}
        </div>

        <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <FileText size={17} className="text-accent" />
            Subtitle fallback
          </div>
          <textarea
            value={subtitleText}
            onChange={(event) => setSubtitleText(event.target.value)}
            rows={9}
            className="mt-3 w-full resize-y rounded-md border border-line px-3 py-2 text-sm leading-6"
          />
          <div className="mt-3 flex justify-end">
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
