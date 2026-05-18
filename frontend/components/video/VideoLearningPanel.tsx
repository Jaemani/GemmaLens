"use client";

import { BookOpenCheck, BookmarkPlus, CheckCircle2, Clock, FileText, Film, Link as LinkIcon, Maximize2, Play, Upload, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { AnalysisProgress } from "@/components/analysis/AnalysisProgress";
import { api } from "@/lib/api";
import { LANGUAGE_OPTIONS } from "@/lib/languages";
import type { AnalysisResult, LocalMediaItem, LocalSubtitleFile, TranscriptResponse, TranscriptSegment, UserProfile } from "@/lib/types";

declare global {
  interface Window {
    YT?: {
      Player: new (elementId: string, options: Record<string, unknown>) => YouTubePlayer;
    };
    onYouTubeIframeAPIReady?: () => void;
  }
}

type VideoMode = "local" | "online";
type LiveCue = {
  text: string;
  gloss: string;
  level: "B1" | "B2" | "C1" | "C2";
  kind: "phrase" | "term";
};

type YouTubePlayer = {
  getCurrentTime?: () => number;
  seekTo?: (seconds: number, allowSeekAhead: boolean) => void;
  destroy?: () => void;
};

const SCENE_WINDOW_SECONDS = 120;
const ONLINE_TRANSCRIPT_SYNC_OFFSET_SECONDS = 0;

const sampleOnlineSources = [
  { label: "ML", url: "https://www.youtube.com/watch?v=eMlx5fFNoYc", detail: "Transformer attention explainer" },
  { label: "Climate", url: "https://www.youtube.com/watch?v=9PFhrpyWV-w", detail: "Climate change explainer" },
  { label: "Economics", url: "https://www.youtube.com/watch?v=3ez10ADR_gM", detail: "Intro economics" },
  { label: "Medical", url: "https://www.youtube.com/watch?v=cUP8bGWln6M", detail: "Virus explainer" },
  { label: "FastAPI", url: "https://www.youtube.com/watch?v=7t2alSnE2-I", detail: "API tutorial" }
];

export function VideoLearningPanel() {
  const [mode, setMode] = useState<VideoMode>("local");
  const [localVideoUrl, setLocalVideoUrl] = useState<string | null>(null);
  const [localVideoName, setLocalVideoName] = useState("");
  const [localMediaRoot, setLocalMediaRoot] = useState("");
  const [localMediaItems, setLocalMediaItems] = useState<LocalMediaItem[]>([]);
  const [localMediaDisabled, setLocalMediaDisabled] = useState(false);
  const [selectedLocalMedia, setSelectedLocalMedia] = useState<LocalMediaItem | null>(null);
  const [selectedKoreanSubtitle, setSelectedKoreanSubtitle] = useState<LocalSubtitleFile | null>(null);
  const [activeSubtitleLanguage, setActiveSubtitleLanguage] = useState<string | null>(null);
  const [localMediaLoading, setLocalMediaLoading] = useState(false);
  const [localPickerOpen, setLocalPickerOpen] = useState(true);
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
  const [sceneLessons, setSceneLessons] = useState<Record<number, AnalysisResult>>({});
  const [sceneLessonTitles, setSceneLessonTitles] = useState<Record<number, string>>({});
  const [autoSceneLessons, setAutoSceneLessons] = useState(false);
  const [sceneBusyKey, setSceneBusyKey] = useState<number | null>(null);
  const [showSubtitleFallback, setShowSubtitleFallback] = useState(true);
  const [cinemaView, setCinemaView] = useState(false);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [selectedLineSegment, setSelectedLineSegment] = useState<TranscriptSegment | null>(null);
  const playerRef = useRef<YouTubePlayer | null>(null);
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const savedPlaybackTimeRef = useRef(0);
  const savedWasPlayingRef = useRef(false);
  const playerElementId = "youtube-learning-player";
  const isAnalyzing = analysisLabel !== null;
  const transcriptTime = mode === "online" ? currentTime + ONLINE_TRANSCRIPT_SYNC_OFFSET_SECONDS : currentTime;

  const activeSegment = useMemo(
    () => activeTranscriptSegment(transcript, transcriptTime),
    [transcriptTime, transcript]
  );
  const pastedVideoId = useMemo(() => extractYouTubeId(youtubeUrl), [youtubeUrl]);
  const youtubeStartSeconds = useMemo(() => extractYouTubeStartSeconds(youtubeUrl), [youtubeUrl]);
  const currentSceneKey = Math.floor(Math.max(0, transcriptTime) / SCENE_WINDOW_SECONDS);
  const sceneText = useMemo(() => sceneWindowText(transcript, currentSceneKey), [currentSceneKey, transcript]);
  const liveCueTick = Math.floor(Math.max(0, transcriptTime) / 3);
  const liveCueText = useMemo(() => currentCueText(transcript, liveCueTick * 3), [liveCueTick, transcript]);
  const liveCues = useMemo(() => extractLiveCues(liveCueText, profile), [liveCueText, profile]);
  const languageModeWarning = useMemo(
    () => learningModeWarning(activeSubtitleLanguage, profile),
    [activeSubtitleLanguage, profile]
  );
  const currentSceneLesson = sceneLessons[currentSceneKey] ?? videoAnalysis;
  const currentSceneLessonTitle = sceneLessonTitles[currentSceneKey] ?? videoAnalysisTitle;
  const selectedLineItems = useMemo(
    () => (selectedLineSegment ? extractSelectedLineItems(selectedLineSegment.text, profile) : []),
    [selectedLineSegment, profile]
  );

  useEffect(() => {
    if (mode !== "online" || !videoId) return;
    let cancelled = false;

    function createPlayer() {
      if (cancelled || !window.YT) return;
      playerRef.current?.destroy?.();
      playerRef.current = new window.YT.Player(playerElementId, {
        videoId,
        playerVars: { modestbranding: 1, rel: 0, start: youtubeStartSeconds || undefined },
        events: {
          onReady: () => {
            if (youtubeStartSeconds > 0) {
              playerRef.current?.seekTo?.(youtubeStartSeconds, true);
              setCurrentTime(youtubeStartSeconds);
            }
          }
        }
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
  }, [mode, videoId, youtubeStartSeconds]);

  useEffect(() => {
    if (!isAnalyzing) return;
    const timer = window.setInterval(() => {
      setAnalysisElapsed((value) => value + 1);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [isAnalyzing]);

  useEffect(() => {
    return () => {
      if (localVideoUrl) URL.revokeObjectURL(localVideoUrl);
    };
  }, [localVideoUrl]);

  useEffect(() => {
    if (mode !== "local") return;
    void loadLocalMediaLibrary();
  }, [mode]);

  useEffect(() => {
    let cancelled = false;
    function loadProfile() {
      api.getProfile()
        .then((loaded) => {
          if (!cancelled) setProfile(loaded);
        })
        .catch(() => undefined);
    }
    loadProfile();
    window.addEventListener("focus", loadProfile);
    return () => {
      cancelled = true;
      window.removeEventListener("focus", loadProfile);
    };
  }, []);

  useEffect(() => {
    if (mode !== "local" || !localVideoRef.current) return;
    const video = localVideoRef.current;
    const restoreTime = savedPlaybackTimeRef.current;
    if (restoreTime > 0 && Math.abs(video.currentTime - restoreTime) > 0.5) {
      video.currentTime = restoreTime;
      setCurrentTime(restoreTime);
    }
    if (savedWasPlayingRef.current) {
      void video.play().catch(() => undefined);
    }
  }, [cinemaView, localVideoUrl, mode]);

  function switchMode(nextMode: VideoMode) {
    setMode(nextMode);
    setCurrentTime(0);
    setError(null);
    setVideoAnalysis(null);
  }

  function openLocalVideo(file: File | null) {
    if (!file) return;
    if (localVideoUrl) URL.revokeObjectURL(localVideoUrl);
    setLocalVideoUrl(URL.createObjectURL(file));
    setLocalVideoName(file.name);
    setCurrentTime(0);
    setError(null);
    setVideoAnalysis(null);
  }

  async function loadLocalMediaLibrary() {
    setLocalMediaLoading(true);
    try {
      const library = await api.listLocalMedia();
      setLocalMediaDisabled(false);
      setLocalMediaRoot(library.root);
      setLocalMediaItems(library.items);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not read the Mac Movies library.";
      if (message.toLowerCase().includes("local media library browsing is disabled")) {
        setLocalMediaDisabled(true);
        setLocalMediaRoot("");
        setLocalMediaItems([]);
      } else {
        setError(message);
      }
    } finally {
      setLocalMediaLoading(false);
    }
  }

  async function openLocalMediaItem(item: LocalMediaItem, subtitle?: LocalSubtitleFile) {
    setSelectedLocalMedia(item);
    setLocalPickerOpen(false);
    setLocalVideoUrl(api.localMediaFileUrl(item.path));
    setLocalVideoName(item.title || item.name);
    setCurrentTime(0);
    setError(null);
    setVideoAnalysis(null);
    const englishSubtitle = subtitle ?? item.subtitles.find((candidate) => candidate.language === "en") ?? item.subtitles[0];
    const koreanSubtitle = item.subtitles.find((candidate) => candidate.language === "ko") ?? null;
    setSelectedKoreanSubtitle(koreanSubtitle);
    if (englishSubtitle) {
      await loadLocalSubtitle(englishSubtitle);
    } else {
      setTranscript(null);
      setSubtitleText("");
      setSourceName("subtitle.srt");
    }
  }

  async function loadLocalSubtitle(subtitle: LocalSubtitleFile) {
    setBusy(true);
    setBusyLabel("Loading local subtitles");
    try {
      const result = await api.getLocalSubtitle(subtitle.path);
      setSubtitleText(result.content);
      setSourceName(result.name);
      setActiveSubtitleLanguage(subtitle.language ?? inferSubtitleLanguage(result.name));
      await parseSubtitle(result.content, result.name);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load this subtitle file.");
    } finally {
      setBusy(false);
      setBusyLabel(null);
    }
  }

  async function readSubtitleFile(file: File | null) {
    if (!file) return;
    setError(null);
    setSourceName(file.name);
    setActiveSubtitleLanguage(inferSubtitleLanguage(file.name));
    try {
      const text = await file.text();
      setSubtitleText(text);
      await parseSubtitle(text, file.name);
    } catch {
      setError("Could not read this subtitle file. Paste the .srt or .vtt text instead.");
    }
  }

  async function parseSubtitle(content = subtitleText, name = sourceName) {
    if (!content.trim()) return;
    setBusy(true);
    setBusyLabel("Parsing subtitles");
    setError(null);
    try {
      const result = await api.parseTranscript({ content, source_name: name });
      setTranscript(result);
      setVideoAnalysis(null);
      setSceneLessons({});
      setSceneLessonTitles({});
      setSourceName(name);
      setActiveSubtitleLanguage((current) => current ?? inferSubtitleLanguage(name));
      if (mode === "online" && !videoId) setVideoId(extractYouTubeId(youtubeUrl));
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
    setBusyLabel("Fetching online transcript");
    setError(null);
    try {
      setVideoId(id);
      setTranscript(null);
      setCurrentTime(youtubeStartSeconds);
      const result = await api.fetchYouTubeTranscript({ url: youtubeUrl, languages: ["en", "ko"] });
      setTranscript(result);
      setActiveSubtitleLanguage("en");
      setSubtitleText("");
      setSourceName("subtitle.srt");
      if (result.source_id) setVideoId(result.source_id);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "YouTube refused the caption fetch from this backend. Try another network/IP, wait a few hours, or upload .srt/.vtt subtitles."
      );
      setShowSubtitleFallback(true);
    } finally {
      setBusy(false);
      setBusyLabel(null);
    }
  }

  function seek(segment: TranscriptSegment) {
    if (mode === "local") {
      const video = localVideoRef.current;
      if (video) {
        video.currentTime = segment.start;
        void video.play().catch(() => undefined);
      }
    } else {
      playerRef.current?.seekTo?.(Math.max(0, segment.start - ONLINE_TRANSCRIPT_SYNC_OFFSET_SECONDS), true);
    }
    setCurrentTime(mode === "online" ? Math.max(0, segment.start - ONLINE_TRANSCRIPT_SYNC_OFFSET_SECONDS) : segment.start);
  }

  function studySubtitleLine(segment: TranscriptSegment) {
    setSelectedLineSegment(segment);
  }

  async function analyzeTranscript() {
    if (!transcript?.plain_text.trim()) return;
    const title = mode === "local" ? `${cleanVideoTitle(localVideoName) || "Local video"} · Watched recap ${formatRecapRange(transcript, transcriptTime)}` : `Online video · Watched recap ${formatRecapRange(transcript, transcriptTime)}`;
    await analyzeText(title, recapText(transcript, transcriptTime), "video_segment");
  }

  async function analyzeCurrentScene() {
    await analyzeSceneWindow(currentSceneKey, true);
  }

  async function analyzeSceneWindow(sceneKey: number, showAsMain: boolean) {
    if (!transcript) return;
    const content = sceneWindowText(transcript, sceneKey);
    if (!content.trim()) return;
    const source = mode === "local" ? cleanVideoTitle(localVideoName) || "Local video" : "Online video";
    const start = sceneKey * SCENE_WINDOW_SECONDS;
    const title = `${source} · Scene ${formatTime(start)}-${formatTime(start + SCENE_WINDOW_SECONDS)}`;
    setSceneBusyKey(sceneKey);
    setAnalysisElapsed(0);
    setAnalysisStep(0);
    setAnalysisLabel("Creating scene source");
    setError(null);
    try {
      const document = await api.createDocument({ title, content, source_type: "video_segment" });
      setAnalysisStep(1);
      setAnalysisLabel("Reading subtitle window");
      setAnalysisStep(2);
      setAnalysisLabel("Running scene analysis");
      const analysis = await api.analyzeVideoDocument(document.id, `Scene ${formatTime(start)}-${formatTime(start + SCENE_WINDOW_SECONDS)}`);
      setAnalysisStep(3);
      setAnalysisLabel("Preparing lesson cards");
      setSceneLessons((current) => ({ ...current, [sceneKey]: analysis }));
      setSceneLessonTitles((current) => ({ ...current, [sceneKey]: title }));
      if (showAsMain) {
        setVideoAnalysis(analysis);
        setVideoAnalysisTitle(title);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not analyze this scene.");
    } finally {
      setAnalysisLabel(null);
      setSceneBusyKey(null);
    }
  }

  async function analyzeText(title: string, content: string, sourceType: string) {
    setBusy(true);
    setBusyLabel(null);
    setAnalysisElapsed(0);
    setAnalysisStep(0);
    setAnalysisLabel(title.includes("Watched recap") ? "Creating watched recap" : "Creating subtitle lesson");
    setError(null);
    try {
      const document = await api.createDocument({ title, content, source_type: sourceType });
      setVideoAnalysisTitle(title);
      setAnalysisStep(1);
      setAnalysisLabel(title.includes("Watched recap") ? "Grouping watched subtitles" : "Reading nearby subtitle lines");
      setAnalysisStep(2);
      setAnalysisLabel(title.includes("Watched recap") ? "Running recap analysis" : "Running subtitle analysis");
      const analysis = await api.analyzeVideoDocument(document.id, title.includes("Watched recap") ? "Building watched recap" : "Building subtitle lesson");
      setAnalysisStep(3);
      setAnalysisLabel("Preparing lesson cards");
      setAnalysisLabel(null);
      setVideoAnalysis(analysis);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not analyze transcript text.");
      setAnalysisLabel(null);
    } finally {
      setBusy(false);
    }
  }

  function capturePlayback() {
    const video = localVideoRef.current;
    if (!video) return;
    savedPlaybackTimeRef.current = video.currentTime;
    savedWasPlayingRef.current = !video.paused;
    setCurrentTime(video.currentTime);
  }

  function openCinemaView() {
    capturePlayback();
    setCinemaView(true);
  }

  function closeCinemaView() {
    capturePlayback();
    setCinemaView(false);
  }

  const playerSurface =
    mode === "local" ? (
      localVideoUrl ? (
        <video
          ref={localVideoRef}
          src={localVideoUrl}
          controls
          className="h-full w-full bg-black"
          onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
          onSeeked={(event) => setCurrentTime(event.currentTarget.currentTime)}
        />
      ) : (
        <EmptyPlayer title="Open a local video" detail="The file stays in this browser session; GemmaLens only reads the subtitles you provide." />
      )
    ) : videoId ? (
      <div key={videoId} id={playerElementId} className="h-full w-full" />
    ) : (
      <EmptyPlayer title="Add an online video URL" detail="Captions become timestamped learning segments when available." />
    );

  if (cinemaView) {
    return (
      <div className="fixed inset-0 z-50 grid bg-neutral-950 text-white lg:grid-cols-[minmax(0,1fr)_420px]">
        <div className="flex min-h-0 flex-col">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wide text-white/50">Cinema view</p>
              <h1 className="truncate text-sm font-semibold">{localVideoName || "Video learning"}</h1>
            </div>
            <button
              type="button"
              onClick={closeCinemaView}
              className="inline-flex items-center gap-2 rounded-md border border-white/15 px-3 py-2 text-sm font-semibold text-white hover:bg-white/10"
            >
              <X size={16} />
              Exit
            </button>
          </div>
          <div className="min-h-0 flex-1 bg-black">{playerSurface}</div>
        </div>
        <div className="min-h-0 border-l border-white/10 bg-neutral-950">
          <TranscriptPane
            transcript={transcript}
            activeSegment={activeSegment}
            selectedLineSegment={selectedLineSegment}
            selectedLineItems={selectedLineItems}
            profile={profile}
            currentTime={transcriptTime}
            onSeek={seek}
            onStudyLine={studySubtitleLine}
            onCloseLineStudy={() => setSelectedLineSegment(null)}
            mode={mode}
            variant="cinema"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
      <section className="space-y-5">
        <div className="rounded-lg border border-line bg-panel p-3 shadow-material">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <h1 className="text-base font-semibold">Video learning</h1>
              <p className="mt-0.5 truncate text-xs text-neutral-500">
                {localVideoName ? cleanVideoTitle(localVideoName) : "Local video with subtitle-based study"}
              </p>
            </div>
            <div className="inline-flex rounded-md border border-line bg-surface p-1">
              <button
                type="button"
                onClick={() => switchMode("local")}
                className={`inline-flex items-center gap-2 rounded px-3 py-1.5 text-sm font-semibold ${
                  mode === "local" ? "bg-panel text-accent shadow-sm" : "text-neutral-600 hover:text-ink"
                }`}
              >
                <Film size={15} />
                Local video
              </button>
              <button
                type="button"
                onClick={() => switchMode("online")}
                className={`inline-flex items-center gap-2 rounded px-3 py-1.5 text-sm font-semibold ${
                  mode === "online" ? "bg-panel text-accent shadow-sm" : "text-neutral-600 hover:text-ink"
                }`}
              >
                <LinkIcon size={15} />
                Online video
              </button>
            </div>
          </div>

          {mode === "local" ? (
            <LocalVideoSetup
              localVideoName={localVideoName}
              localMediaRoot={localMediaRoot}
              localMediaItems={localMediaItems}
              selectedLocalMedia={selectedLocalMedia}
              selectedKoreanSubtitle={selectedKoreanSubtitle}
              localMediaLoading={localMediaLoading}
              localMediaDisabled={localMediaDisabled}
              localPickerOpen={localPickerOpen}
              busy={busy}
              busyLabel={busyLabel}
              onTogglePicker={() => setLocalPickerOpen((value) => !value)}
              onOpenVideo={openLocalVideo}
              onReadSubtitle={readSubtitleFile}
              onRefreshLibrary={loadLocalMediaLibrary}
              onSelectMedia={openLocalMediaItem}
              onSelectSubtitle={loadLocalSubtitle}
            />
          ) : (
            <OnlineVideoSetup
              youtubeUrl={youtubeUrl}
              pastedVideoId={pastedVideoId}
              busy={busy}
              busyLabel={busyLabel}
              onUrlChange={setYoutubeUrl}
              onFetch={fetchYouTube}
            />
          )}
        </div>

        <div className="overflow-hidden rounded-lg border border-line bg-panel shadow-material">
          <div className="flex items-center justify-between border-b border-line px-4 py-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Player</p>
            <button
              type="button"
              onClick={openCinemaView}
              className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-1.5 text-xs font-semibold text-ink hover:bg-surface"
            >
              <Maximize2 size={14} />
              Cinema view
            </button>
          </div>
          <div className="aspect-video bg-black">{playerSurface}</div>
        </div>

        <SubtitleWorkspace
          mode={mode}
          transcript={transcript}
          subtitleText={subtitleText}
          sourceName={sourceName}
          busy={busy}
          busyLabel={busyLabel}
          error={error}
          showSubtitleFallback={showSubtitleFallback}
          isAnalyzing={isAnalyzing}
          analysisElapsed={analysisElapsed}
          analysisStep={analysisStep}
          analysisLabel={analysisLabel}
          sceneText={sceneText}
          liveCues={liveCues}
          profile={profile}
          languageModeWarning={languageModeWarning}
          currentTime={transcriptTime}
          autoSceneLessons={autoSceneLessons}
          sceneBusyKey={sceneBusyKey}
          currentSceneKey={currentSceneKey}
          sceneLessonReady={Boolean(sceneLessons[currentSceneKey])}
          onToggleAutoSceneLessons={() => setAutoSceneLessons((value) => !value)}
          onToggleFallback={() => setShowSubtitleFallback((value) => !value)}
          onSourceNameChange={setSourceName}
          onSubtitleTextChange={setSubtitleText}
          onReadSubtitle={readSubtitleFile}
          onParseSubtitle={() => parseSubtitle()}
          onAnalyzeCurrentScene={analyzeCurrentScene}
          onAnalyzeTranscript={analyzeTranscript}
        />

        {currentSceneLesson ? <VideoInlineLesson analysis={currentSceneLesson} title={currentSceneLessonTitle} /> : null}
      </section>

      <TranscriptPane
        transcript={transcript}
        activeSegment={activeSegment}
        selectedLineSegment={selectedLineSegment}
        selectedLineItems={selectedLineItems}
        profile={profile}
        currentTime={transcriptTime}
        onSeek={seek}
        onStudyLine={studySubtitleLine}
        onCloseLineStudy={() => setSelectedLineSegment(null)}
        mode={mode}
      />
    </div>
  );
}

function LocalVideoSetup({
  localVideoName,
  localMediaRoot,
  localMediaItems,
  selectedLocalMedia,
  selectedKoreanSubtitle,
  localMediaLoading,
  localMediaDisabled,
  localPickerOpen,
  busy,
  busyLabel,
  onTogglePicker,
  onOpenVideo,
  onReadSubtitle,
  onRefreshLibrary,
  onSelectMedia,
  onSelectSubtitle
}: {
  localVideoName: string;
  localMediaRoot: string;
  localMediaItems: LocalMediaItem[];
  selectedLocalMedia: LocalMediaItem | null;
  selectedKoreanSubtitle: LocalSubtitleFile | null;
  localMediaLoading: boolean;
  localMediaDisabled: boolean;
  localPickerOpen: boolean;
  busy: boolean;
  busyLabel: string | null;
  onTogglePicker: () => void;
  onOpenVideo: (file: File | null) => void;
  onReadSubtitle: (file: File | null) => void;
  onRefreshLibrary: () => void;
  onSelectMedia: (item: LocalMediaItem, subtitle?: LocalSubtitleFile) => void;
  onSelectSubtitle: (subtitle: LocalSubtitleFile) => void;
}) {
  if (selectedLocalMedia && !localPickerOpen) {
    return (
      <div className="mt-3 rounded-md border border-line bg-surface px-3 py-2">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0 flex items-center gap-2">
            <p className="truncate text-sm font-semibold text-ink">{cleanVideoTitle(selectedLocalMedia.title || localVideoName || selectedLocalMedia.name)}</p>
            <span className="shrink-0 rounded-full bg-panel px-2 py-0.5 text-xs font-semibold text-neutral-600">{selectedLocalMedia.subtitles.length} subtitles</span>
            {selectedKoreanSubtitle ? <span className="hidden shrink-0 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-semibold text-accent md:inline">KO support</span> : null}
          </div>
          <button
            type="button"
            onClick={onTogglePicker}
            className="shrink-0 rounded-md border border-line bg-panel px-3 py-1.5 text-xs font-semibold text-ink hover:bg-white"
          >
            Change
          </button>
        </div>
        {busyLabel ? <p className="mt-2 rounded-md bg-blue-50 px-3 py-2 text-sm font-medium text-accent">{busyLabel}...</p> : null}
      </div>
    );
  }

  return (
    <div className="mt-5 space-y-4">
      <div className="rounded-md border border-line bg-surface p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-ink">Mac Movies library</p>
            <p className="mt-1 text-xs leading-5 text-neutral-500">
              {localMediaRoot ? localMediaRoot : "~/Movies"} · finds local videos and nearby English/Korean subtitles.
            </p>
          </div>
          <button
            type="button"
            onClick={selectedLocalMedia ? onTogglePicker : onRefreshLibrary}
            className="rounded-md border border-line bg-panel px-3 py-1.5 text-xs font-semibold text-ink hover:bg-white"
          >
            {selectedLocalMedia ? (localPickerOpen ? "Collapse" : "Change") : localMediaLoading ? "Scanning..." : "Refresh"}
          </button>
        </div>
        {selectedLocalMedia && !localPickerOpen ? (
          <div className="mt-3 rounded-md border border-line bg-panel p-3">
            <p className="truncate text-sm font-semibold text-ink">{selectedLocalMedia.title}</p>
            <p className="mt-1 text-xs text-neutral-500">
              {selectedLocalMedia.subtitles.length} subtitles found · click Change to pick another file
            </p>
          </div>
        ) : localMediaItems.length ? (
          <div className="mt-3 max-h-56 overflow-y-auto rounded-md border border-line bg-panel">
            {localMediaItems.map((item) => (
              <div key={item.path} className={`border-t border-line p-3 first:border-t-0 ${selectedLocalMedia?.path === item.path ? "bg-blue-50" : ""}`}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <button type="button" onClick={() => onSelectMedia(item)} className="min-w-0 text-left">
                    <span className="block truncate text-sm font-semibold text-ink">{item.title}</span>
                    <span className="mt-1 block truncate text-xs text-neutral-500">{item.name}</span>
                  </button>
                  <span className="rounded-full bg-surface px-2 py-1 text-xs font-semibold text-neutral-600">{item.subtitles.length} subtitles</span>
                </div>
                {item.subtitles.length ? (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {item.subtitles.map((subtitle) => (
                      <button
                        key={subtitle.path}
                        type="button"
                        onClick={() => {
                          if (selectedLocalMedia?.path !== item.path) onSelectMedia(item, subtitle);
                          else onSelectSubtitle(subtitle);
                        }}
                        className="rounded-full border border-line bg-white px-2.5 py-1 text-xs font-semibold text-neutral-700 hover:border-accent hover:text-accent"
                      >
                        {subtitle.language ? subtitle.language.toUpperCase() : "SUB"} · {subtitle.name}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-3 rounded-md border border-dashed border-line bg-panel p-3 text-sm leading-6 text-neutral-600">
            {localMediaLoading
              ? "Scanning Movies..."
              : localMediaDisabled
                ? "Local media browsing is disabled for the public demo. Use the manual file picker below, or enable it only for a curated demo folder."
                : "No videos found yet. Put the movie folder under ~/Movies, or use the manual file picker below."}
          </p>
        )}
        {selectedKoreanSubtitle ? (
          <p className="mt-3 rounded-md bg-blue-50 px-3 py-2 text-xs font-medium text-accent">
            Korean subtitle detected: {selectedKoreanSubtitle.name}. English subtitles remain the learning source; Korean can be used as timed meaning support next.
          </p>
        ) : null}
      </div>

      <div className="grid gap-3 md:grid-cols-2">
      <label className="flex cursor-pointer items-center justify-between gap-3 rounded-md border border-line bg-surface px-4 py-3 hover:bg-white">
        <span>
          <span className="block text-sm font-semibold text-ink">Open video manually</span>
          <span className="mt-1 block text-xs text-neutral-500">{localVideoName || "MP4, MOV, MKV, WebM depending on browser support"}</span>
        </span>
        <Upload size={18} className="text-accent" />
        <input type="file" accept="video/*,.mkv" className="hidden" onChange={(event) => onOpenVideo(event.target.files?.[0] ?? null)} />
      </label>
      <label className="flex cursor-pointer items-center justify-between gap-3 rounded-md border border-line bg-surface px-4 py-3 hover:bg-white">
        <span>
          <span className="block text-sm font-semibold text-ink">Load English subtitles</span>
          <span className="mt-1 block text-xs text-neutral-500">SRT, VTT, or timestamped transcript text</span>
        </span>
        <FileText size={18} className="text-accent" />
        <input type="file" accept=".srt,.vtt,text/vtt,application/x-subrip,text/plain" className="hidden" onChange={(event) => onReadSubtitle(event.target.files?.[0] ?? null)} />
      </label>
      {busyLabel ? (
        <p className="md:col-span-2 rounded-md bg-blue-50 px-3 py-2 text-sm font-medium text-accent">{busyLabel}...</p>
      ) : (
        <p className="md:col-span-2 text-xs leading-5 text-neutral-500">
          Local video files are not uploaded to GemmaLens. The browser plays the file directly; the subtitle text becomes the learning source.
        </p>
      )}
      {busy ? null : null}
      </div>
    </div>
  );
}

function OnlineVideoSetup({
  youtubeUrl,
  pastedVideoId,
  busy,
  busyLabel,
  onUrlChange,
  onFetch
}: {
  youtubeUrl: string;
  pastedVideoId: string | null;
  busy: boolean;
  busyLabel: string | null;
  onUrlChange: (value: string) => void;
  onFetch: () => void;
}) {
  return (
    <div className="mt-5">
      <div className="grid gap-3 md:grid-cols-[1fr_auto]">
        <input
          value={youtubeUrl}
          onChange={(event) => onUrlChange(event.target.value)}
          placeholder="YouTube URL"
          className="rounded-md border border-line px-3 py-2 text-sm"
        />
        <button
          type="button"
          onClick={onFetch}
          disabled={busy || !youtubeUrl.trim()}
          className="inline-flex items-center justify-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          {busyLabel === "Fetching online transcript" ? <Clock size={16} className="animate-spin" /> : <LinkIcon size={16} />}
          {busyLabel === "Fetching online transcript" ? "Fetching..." : "Fetch transcript"}
        </button>
      </div>
      <div className="mt-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Try a sample</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {sampleOnlineSources.map((source) => (
            <button
              key={source.url}
              type="button"
              onClick={() => onUrlChange(source.url)}
              className="rounded-full border border-line bg-surface px-3 py-1.5 text-xs font-semibold text-ink hover:border-accent hover:text-accent"
              title={source.detail}
            >
              {source.label}
            </button>
          ))}
        </div>
      </div>
      {busyLabel ? <p className="mt-3 rounded-md bg-blue-50 px-3 py-2 text-sm font-medium text-accent">{busyLabel}. Caption availability depends on the source.</p> : null}
      {youtubeUrl.trim() && !pastedVideoId ? <p className="mt-2 text-xs text-amber-700">This does not look like a supported YouTube URL yet.</p> : null}
    </div>
  );
}

function SubtitleWorkspace({
  mode,
  transcript,
  subtitleText,
  sourceName,
  busy,
  busyLabel,
  error,
  showSubtitleFallback,
  isAnalyzing,
  analysisElapsed,
  analysisStep,
  analysisLabel,
  sceneText,
  liveCues,
  profile,
  languageModeWarning,
  currentTime,
  autoSceneLessons,
  sceneBusyKey,
  currentSceneKey,
  sceneLessonReady,
  onToggleFallback,
  onToggleAutoSceneLessons,
  onSourceNameChange,
  onSubtitleTextChange,
  onReadSubtitle,
  onParseSubtitle,
  onAnalyzeCurrentScene,
  onAnalyzeTranscript
}: {
  mode: VideoMode;
  transcript: TranscriptResponse | null;
  subtitleText: string;
  sourceName: string;
  busy: boolean;
  busyLabel: string | null;
  error: string | null;
  showSubtitleFallback: boolean;
  isAnalyzing: boolean;
  analysisElapsed: number;
  analysisStep: number;
  analysisLabel: string | null;
  sceneText: string;
  liveCues: LiveCue[];
  profile: UserProfile | null;
  languageModeWarning: string | null;
  currentTime: number;
  autoSceneLessons: boolean;
  sceneBusyKey: number | null;
  currentSceneKey: number;
  sceneLessonReady: boolean;
  onToggleFallback: () => void;
  onToggleAutoSceneLessons: () => void;
  onSourceNameChange: (value: string) => void;
  onSubtitleTextChange: (value: string) => void;
  onReadSubtitle: (file: File | null) => void;
  onParseSubtitle: () => void;
  onAnalyzeCurrentScene: () => void;
  onAnalyzeTranscript: () => void;
}) {
  if (transcript) {
    return (
      <div className="rounded-lg border border-line bg-panel p-4 shadow-material">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold">Scene study controls</p>
            <p className="mt-1 text-xs text-neutral-500">
              {transcript.segments.length} subtitle lines ready. Study the current 2-minute scene, or recap the part you have watched.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={onToggleAutoSceneLessons}
              className={`inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-semibold ${
                autoSceneLessons ? "border-accent bg-blue-50 text-accent" : "border-line text-ink hover:bg-surface"
              }`}
            >
              <BookOpenCheck size={16} />
              Auto while watching
            </button>
            <button
              type="button"
              onClick={onAnalyzeCurrentScene}
              disabled={busy || sceneBusyKey !== null || !sceneText.trim()}
              className="inline-flex items-center gap-2 rounded-md border border-line px-4 py-2 text-sm font-semibold text-ink hover:bg-surface disabled:opacity-50"
            >
              <BookOpenCheck size={16} />
              {sceneBusyKey === currentSceneKey ? "Studying scene..." : sceneLessonReady ? "Refresh current 2 min" : "Study current 2 min"}
            </button>
            <button
              type="button"
              onClick={onAnalyzeTranscript}
              disabled={busy || !transcript.plain_text.trim()}
              className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              <BookOpenCheck size={16} />
              Deep recap
            </button>
          </div>
        </div>
        <div className="mt-3 grid gap-2 text-xs leading-5 text-neutral-600 md:grid-cols-3">
          <p>
            <span className="font-semibold text-ink">Auto while watching</span> follows the current subtitle lines.
          </p>
          <p>
            <span className="font-semibold text-ink">Study current 2 min</span> builds a focused scene lesson.
          </p>
          <p>
            <span className="font-semibold text-ink">Deep recap</span> reviews watched 15-minute blocks.
          </p>
        </div>
        {languageModeWarning ? (
          <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm leading-6 text-amber-900">
            {languageModeWarning}
          </div>
        ) : null}
        {profile && normalizeLanguageName(profile.support_language) !== "Korean" && normalizeLanguageName(profile.support_language) !== "English" ? (
          <div className="mt-3 rounded-md border border-line bg-surface px-3 py-2 text-xs leading-5 text-neutral-600">
            Live cues use lightweight local labels. Use Study current 2 min or Deep recap for full {normalizeLanguageName(profile.support_language)} explanations from the model.
          </div>
        ) : null}
        {autoSceneLessons && liveCues.length ? (
          <div className="mt-3 rounded-md border border-line bg-surface p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Live cues near {formatTime(currentTime)}</p>
              <span className="text-xs font-semibold text-neutral-500">
                {profile?.learning_language ?? "English"} to {profile?.support_language ?? "Korean"} · {profile?.target_level ?? "C1"}
              </span>
            </div>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {liveCues.map((cue) => (
                <LiveCueCard key={`${cue.kind}:${cue.text}`} cue={cue} />
              ))}
            </div>
          </div>
        ) : autoSceneLessons ? (
          <div className="mt-3 rounded-md border border-line bg-surface p-3 text-sm leading-6 text-neutral-600">
            No {profile?.target_level ?? "target-level"} cue in this short subtitle window. Keep watching, or use Study current 2 min for a deeper model pass.
          </div>
        ) : null}
        {isAnalyzing ? (
          <div className="mt-4">
            <AnalysisProgress
              title={mode === "local" ? "Analyzing local subtitle lesson" : "Analyzing online transcript"}
              elapsed={analysisElapsed}
              step={analysisStep}
              currentLabel={analysisLabel}
              labels={["Creating source", "Reading subtitles", "Running model", "Preparing lesson", "Showing lesson"]}
              hint="Keep watching. The lesson appears beside the video instead of opening a separate document page."
            />
          </div>
        ) : null}
        {error ? <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">{error}</p> : null}
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
      <button
        type="button"
        onClick={onToggleFallback}
        className="inline-flex items-center rounded-md border border-line px-4 py-2 text-sm font-semibold text-ink hover:bg-surface"
      >
        {showSubtitleFallback ? "Hide subtitle text" : mode === "local" ? "Paste subtitles manually" : "Captions unavailable? Paste subtitles"}
      </button>
      {showSubtitleFallback ? (
        <>
          <div className="mt-3 rounded-md border border-line bg-surface p-3 text-sm leading-6 text-neutral-700">
            <p className="font-semibold text-ink">{mode === "local" ? "Local subtitle source" : "Caption fallback"}</p>
            <p className="mt-1">
              {mode === "local"
                ? "Load an .srt/.vtt file from the same movie, or paste subtitle text. GemmaLens uses the timestamps to sync reading support with playback."
                : "If YouTube blocks caption APIs, upload/paste an .srt/.vtt file or transcript text from a source you can access."}
            </p>
            <label className="mt-3 inline-flex cursor-pointer items-center gap-2 rounded-md border border-line bg-panel px-3 py-2 text-sm font-semibold text-ink hover:bg-white">
              <FileText size={16} className="text-accent" />
              Upload .srt/.vtt
              <input
                type="file"
                accept=".srt,.vtt,text/vtt,application/x-subrip,text/plain"
                className="hidden"
                onChange={(event) => onReadSubtitle(event.target.files?.[0] ?? null)}
              />
            </label>
          </div>
          <input
            value={sourceName}
            onChange={(event) => onSourceNameChange(event.target.value)}
            className="mt-3 w-full rounded-md border border-line px-3 py-2 text-sm"
            placeholder="subtitle filename"
          />
          <textarea
            value={subtitleText}
            onChange={(event) => onSubtitleTextChange(event.target.value)}
            rows={9}
            className="mt-3 w-full resize-y rounded-md border border-line px-3 py-2 text-sm leading-6"
            placeholder="Paste .srt, .vtt, or timestamped transcript text."
          />
          <div className="mt-3 flex justify-end">
            <button
              type="button"
              onClick={onParseSubtitle}
              disabled={busy || !subtitleText.trim()}
              className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {busyLabel === "Parsing subtitles" ? "Parsing..." : "Parse subtitle"}
            </button>
          </div>
        </>
      ) : null}
      {error ? <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">{error}</p> : null}
    </div>
  );
}

function LiveCueCard({ cue }: { cue: LiveCue }) {
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  async function saveCue() {
    setSaving(true);
    try {
      await api.saveDictionaryItem({
        item_type: cue.kind === "phrase" ? "phrase" : "term",
        text: cue.text,
        meaning: dictionaryMeaning({
          type: cue.kind === "phrase" ? "phrase" : "term",
          text: cue.text,
          meaning: cue.gloss
        })
      });
      setSaved(true);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-md border border-line bg-panel px-3 py-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-ink">{cue.text}</p>
          <span className="mt-1 inline-flex rounded-full bg-surface px-2 py-0.5 text-[10px] font-semibold text-neutral-500">
            {cue.level} · {cue.kind}
          </span>
        </div>
        <button
          type="button"
          onClick={saveCue}
          disabled={saved || saving}
          className="inline-flex shrink-0 items-center gap-1 rounded-md border border-line bg-surface px-2 py-1 text-xs font-semibold text-neutral-700 hover:bg-white disabled:opacity-60"
        >
          {saved ? <CheckCircle2 size={12} /> : <BookmarkPlus size={12} />}
          {saved ? "Saved" : saving ? "..." : "Save"}
        </button>
      </div>
      {cue.gloss ? <p className="mt-2 text-xs leading-5 text-neutral-600">{cue.gloss}</p> : null}
    </div>
  );
}

function SelectedLineStudyPanel({
  segment,
  items,
  profile,
  onClose,
  variant = "default"
}: {
  segment: TranscriptSegment;
  items: LiveCue[];
  profile: UserProfile | null;
  onClose: () => void;
  variant?: "default" | "cinema";
}) {
  const cinema = variant === "cinema";
  const [translation, setTranslation] = useState("");
  const [translationBusy, setTranslationBusy] = useState(false);

  useEffect(() => {
    if (!profile || !segment.text.trim()) return;
    let cancelled = false;
    setTranslation("");
    setTranslationBusy(true);
    api.translateText({
      source_language: profile.learning_language,
      target_language: profile.support_language,
      text: segment.text
    })
      .then((result) => {
        if (!cancelled) setTranslation(result.translated_text);
      })
      .catch(() => {
        if (!cancelled) setTranslation("");
      })
      .finally(() => {
        if (!cancelled) setTranslationBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [profile, segment.index, segment.text]);

  return (
    <section className={cinema ? "rounded-lg border border-white/10 bg-white/5 p-3 text-white" : "rounded-lg border border-line bg-panel p-4 shadow-material"}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className={cinema ? "text-xs font-semibold uppercase tracking-wide text-white/45" : "text-xs font-semibold uppercase tracking-wide text-neutral-500"}>
            Line study
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className={cinema ? "rounded-full bg-white/10 px-2.5 py-1 text-xs font-semibold text-white/65" : "rounded-full bg-surface px-2.5 py-1 text-xs font-semibold text-neutral-600"}>{formatTime(segment.start)}</span>
            <span className={cinema ? "rounded-full bg-white/10 px-2.5 py-1 text-xs font-semibold text-white/65" : "rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-accent"}>
              {profile?.learning_language ?? "English"} to {profile?.support_language ?? "explanation"}
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className={cinema ? "rounded-md border border-white/15 px-3 py-1.5 text-xs font-semibold text-white/70 hover:bg-white/10" : "rounded-md border border-line px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-surface"}
        >
          Close
        </button>
      </div>
      <p className={cinema ? "mt-3 rounded-md bg-white/10 px-3 py-2 text-sm leading-6 text-white/90" : "mt-3 rounded-md bg-surface px-3 py-2 text-sm leading-6 text-ink"}>{segment.text}</p>
      <div className={cinema ? "mt-2 rounded-md border border-white/10 bg-black/20 px-3 py-2" : "mt-2 rounded-md border border-line bg-surface px-3 py-2"}>
        <p className={cinema ? "text-xs font-semibold uppercase tracking-wide text-white/45" : "text-xs font-semibold uppercase tracking-wide text-neutral-500"}>
          Meaning in {profile?.support_language ?? "explanation language"}
        </p>
        <p className={cinema ? "mt-1 text-sm leading-6 text-white/75" : "mt-1 text-sm leading-6 text-neutral-700"}>
          {translationBusy ? "Translating this line..." : translation || "No translation available for this line yet."}
        </p>
      </div>
      {items.length ? (
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {items.map((item) => (
            <LiveCueCard key={`${segment.index}:${item.kind}:${item.text}`} cue={item} />
          ))}
        </div>
      ) : (
        <p className={cinema ? "mt-3 rounded-md bg-white/10 px-3 py-2 text-sm leading-6 text-white/65" : "mt-3 rounded-md bg-surface px-3 py-2 text-sm leading-6 text-neutral-600"}>
          No separable study items found in this short line.
        </p>
      )}
    </section>
  );
}

function TranscriptPane({
  transcript,
  activeSegment,
  selectedLineSegment,
  selectedLineItems,
  profile,
  currentTime,
  onSeek,
  onStudyLine,
  onCloseLineStudy,
  mode,
  variant = "default"
}: {
  transcript: TranscriptResponse | null;
  activeSegment: TranscriptSegment | undefined;
  selectedLineSegment: TranscriptSegment | null;
  selectedLineItems: LiveCue[];
  profile: UserProfile | null;
  currentTime: number;
  onSeek: (segment: TranscriptSegment) => void;
  onStudyLine: (segment: TranscriptSegment) => void;
  onCloseLineStudy: () => void;
  mode: VideoMode;
  variant?: "default" | "cinema";
}) {
  const activeButtonRef = useRef<HTMLDivElement | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const active = activeButtonRef.current;
    const container = scrollContainerRef.current;
    if (!active || !container) return;
    const target = active.offsetTop - container.clientHeight / 2 + active.clientHeight / 2;
    container.scrollTo({ top: Math.max(0, target) });
  }, [activeSegment?.index]);

  return (
    <aside
      className={
        variant === "cinema"
          ? "flex h-full min-h-0 flex-col bg-neutral-950 text-white"
          : "self-start rounded-lg border border-line bg-panel shadow-material xl:sticky xl:top-4"
      }
    >
      <div className={variant === "cinema" ? "border-b border-white/10 p-4" : "border-b border-line p-4"}>
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-semibold">Subtitle timeline</h2>
          <span
            className={
              variant === "cinema"
                ? "inline-flex items-center gap-1 rounded-full bg-white/10 px-2.5 py-1 text-xs font-semibold text-white/70"
                : "inline-flex items-center gap-1 rounded-full bg-surface px-2.5 py-1 text-xs font-semibold text-neutral-600"
            }
          >
            <Clock size={13} />
            {formatTime(currentTime)}
          </span>
        </div>
        {transcript?.warning ? <p className="mt-2 text-xs text-amber-700">{transcript.warning}</p> : null}
      </div>
      <div ref={scrollContainerRef} className={variant === "cinema" ? "min-h-0 flex-1 overflow-y-auto p-2" : "max-h-[720px] overflow-y-auto p-2"}>
        {transcript ? (
          transcript.segments.map((segment) => {
            const selected = selectedLineSegment?.index === segment.index;
            return (
              <div key={segment.index}>
                <div
                  ref={activeSegment?.index === segment.index ? activeButtonRef : null}
                  className={`group w-full rounded-md p-3 text-left text-sm leading-6 transition ${
                    activeSegment?.index === segment.index
                      ? variant === "cinema"
                        ? "bg-white text-neutral-950"
                        : "bg-blue-50 text-ink"
                      : selected
                        ? variant === "cinema"
                          ? "bg-white/10 text-white"
                          : "bg-surface text-ink"
                        : variant === "cinema"
                          ? "text-white/75 hover:bg-white/10"
                          : "hover:bg-surface"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <button type="button" onClick={() => onSeek(segment)} className="min-w-0 flex-1 text-left">
                      <span className={variant === "cinema" ? "mb-1 block text-xs font-semibold text-white/45" : "mb-1 block text-xs font-semibold text-accent"}>
                        {formatTime(segment.start)}
                      </span>
                      {segment.text}
                    </button>
                    <button
                      type="button"
                      onClick={() => onStudyLine(segment)}
                      className={
                        variant === "cinema"
                          ? "shrink-0 rounded-md border border-white/15 px-2 py-1 text-xs font-semibold text-white/70 opacity-0 transition hover:bg-white/10 focus:opacity-100 group-hover:opacity-100"
                          : "shrink-0 rounded-md border border-line bg-panel px-2 py-1 text-xs font-semibold text-neutral-700 opacity-0 transition hover:bg-white focus:opacity-100 group-hover:opacity-100"
                      }
                    >
                      Study
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="space-y-3 p-4 text-sm leading-6 text-neutral-600">
            <p className="font-semibold text-ink">No subtitles loaded</p>
            <p>
              {mode === "local"
                ? "Open a video file and load its English subtitles. Timeline lines will sync with the player."
                : "Fetch online captions or paste subtitles to turn timeline segments into language lessons."}
            </p>
            <div className="rounded-md bg-surface p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Learning flow</p>
              <ol className="mt-2 space-y-1">
                <li>1. Open a video and subtitle file.</li>
                <li>2. Click a timestamp or watch normally.</li>
                <li>3. Analyze one scene or all subtitles.</li>
              </ol>
            </div>
          </div>
        )}
      </div>
      {selectedLineSegment ? (
        <div className={variant === "cinema" ? "border-t border-white/10 p-3" : "border-t border-line p-3"}>
          <SelectedLineStudyPanel
            segment={selectedLineSegment}
            items={selectedLineItems}
            profile={profile}
            onClose={onCloseLineStudy}
            variant={variant}
          />
        </div>
      ) : null}
    </aside>
  );
}

function VideoInlineLesson({ analysis, title }: { analysis: AnalysisResult; title: string }) {
  const titleParts = splitLessonTitle(title);
  const concepts = (analysis.concepts ?? []).slice(0, 4);
  const terms = analysis.terms.slice(0, 6);
  const phrases = analysis.phrases.slice(0, 5);
  const sentence = analysis.sentences[0];

  return (
    <section className="rounded-lg border border-line bg-panel shadow-material">
      <div className="border-b border-line p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Video lesson</p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold">{titleParts.name || "Current video lesson"}</h2>
          {titleParts.kind ? <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-accent">{titleParts.kind}</span> : null}
          {titleParts.time ? <span className="rounded-full bg-surface px-2.5 py-1 text-xs font-semibold text-neutral-600">{titleParts.time}</span> : null}
        </div>
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
              type: "concept",
              text: concept.concept,
              meaning: concept.explanation || concept.why_it_matters,
              source: concept.source_sentence
            }))}
          />
        ) : null}
        <CompactVideoList
          title="Words to listen for"
          rows={terms.map((term) => ({
            type: "term",
            text: term.term,
            meaning: term.meaning,
            native: cleanedNativeGloss(term.support_language_meaning),
            source: term.source_sentence,
            meta: [term.learning_priority, term.difficulty].filter(Boolean).join(" · ")
          }))}
        />
        <CompactVideoList
          title="Useful spoken expressions"
          rows={phrases.map((phrase) => ({
            type: "phrase",
            text: phrase.phrase,
            meaning: phrase.explanation,
            native: cleanedNativeGloss(phrase.support_language_explanation),
            source: phrase.source_sentence,
            meta: [phrase.learning_priority, phrase.function].filter(Boolean).join(" · ")
          }))}
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

type CompactVideoRow = {
  type?: "term" | "phrase" | "sentence" | "concept";
  text: string;
  meaning?: string;
  native?: string;
  source?: string;
  meta?: string;
};

function CompactVideoList({ title, rows }: { title: string; rows: CompactVideoRow[] }) {
  const [saved, setSaved] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState<string | null>(null);
  if (!rows.length) return null;

  async function saveRow(row: CompactVideoRow) {
    const key = `${row.type || "term"}:${row.text}`;
    setSaving(key);
    try {
      await api.saveDictionaryItem({
        item_type: row.type || "term",
        text: row.text,
        meaning: dictionaryMeaning(row),
        source_sentence: row.source
      });
      setSaved((current) => new Set(current).add(key));
    } finally {
      setSaving(null);
    }
  }

  return (
    <div className="rounded-md border border-line bg-surface p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{title}</p>
      <div className="mt-3 grid gap-3">
        {rows.map((row) => (
          <div key={`${title}:${row.text}`} className="border-t border-line pt-3 first:border-t-0 first:pt-0">
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm font-semibold text-ink">{row.text}</p>
              <button
                type="button"
                onClick={() => saveRow(row)}
                disabled={saved.has(`${row.type || "term"}:${row.text}`) || saving === `${row.type || "term"}:${row.text}`}
                className="inline-flex shrink-0 items-center gap-1 rounded-md border border-line bg-panel px-2 py-1 text-xs font-semibold text-neutral-700 hover:bg-white disabled:opacity-60"
              >
                {saved.has(`${row.type || "term"}:${row.text}`) ? <CheckCircle2 size={12} /> : <BookmarkPlus size={12} />}
                {saved.has(`${row.type || "term"}:${row.text}`) ? "Saved" : saving === `${row.type || "term"}:${row.text}` ? "..." : "Save"}
              </button>
            </div>
            {row.meta ? <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">{row.meta.replaceAll("_", " ")}</p> : null}
            {row.native ? <p className="mt-2 rounded-md bg-blue-50 px-3 py-2 text-sm leading-6 text-accent">{row.native}</p> : null}
            <p className="mt-2 text-sm leading-6 text-neutral-700">{displayMeaning(row)}</p>
            {row.source ? <p className="mt-1 text-xs leading-5 text-neutral-500">{truncate(row.source, 180)}</p> : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function displayMeaning(row: CompactVideoRow) {
  return cleanMeaning(row.meaning) || cleanMeaning(row.native) || fallbackMeaning(row);
}

function dictionaryMeaning(row: CompactVideoRow) {
  return cleanMeaning(row.meaning) || cleanMeaning(row.native) || fallbackMeaning(row);
}

function cleanMeaning(value?: string | null) {
  const text = (value ?? "").replace(/\s+/g, " ").trim();
  if (!text) return "";
  const weakFallbacks = [
    "현재 자막에서 눈에 띄는 긴 단어입니다. 문맥으로 의미를 확인하세요.",
    "A noticeable long word from the current subtitle line. Use the source line to confirm the meaning."
  ];
  return weakFallbacks.some((fallback) => text.toLowerCase() === fallback.toLowerCase()) ? "" : text;
}

function fallbackMeaning(row: CompactVideoRow) {
  const source = truncate(row.source || "", 160);
  const text = row.text.trim();
  if (row.type === "concept") {
    return source ? `${text} is a concept used in this scene. Source: ${source}` : `${text} is a concept to review from this video scene.`;
  }
  if (row.type === "phrase") {
    return source ? `Spoken expression from this scene. Source: ${source}` : "Spoken expression to review from this video scene.";
  }
  if (row.type === "sentence") {
    return source ? `Sentence pattern from this scene. Source: ${source}` : "Sentence pattern to review from this video scene.";
  }
  return source ? `Term used in this scene. Source: ${source}` : "Term to review from this video scene.";
}

function truncate(value: string, limit: number) {
  const normalized = value.split(/\s+/).join(" ").trim();
  if (normalized.length <= limit) return normalized;
  return `${normalized.slice(0, limit).trim()}...`;
}

function splitLessonTitle(title: string) {
  const fallback = title || "Current video lesson";
  const [rawName, rawMeta] = fallback.split(" · ", 2);
  const name = cleanVideoTitle(rawName);
  const dedupedName = name.includes(" / ") ? dedupeTitleParts(name.split(" / ").map((part) => cleanVideoTitle(part)).filter(Boolean)) : name;
  if (!rawMeta) return { name: dedupedName, kind: "", time: "" };
  const sceneMatch = rawMeta.match(/^(Scene|Watched recap)\s+(.+)$/i);
  if (sceneMatch) return { name: dedupedName, kind: sceneMatch[1], time: sceneMatch[2] };
  return { name: dedupedName, kind: rawMeta, time: "" };
}

function cleanVideoTitle(value: string) {
  const cleaned = value
    .split("/")
    .map((part) =>
      part
        .replace(/\.[a-z0-9]+$/i, "")
        .replace(/\s*[_-]\s*Full documentary\s*/i, "")
        .replace(/\s*[_-]\s*Tribeca Film Festival official selection\s*/i, "")
        .replace(/\s+/g, " ")
        .trim()
    )
    .filter(Boolean);
  return dedupeTitleParts(cleaned).trim();
}

function dedupeTitleParts(parts: string[]) {
  const seen = new Set<string>();
  return parts
    .filter((part) => {
      const key = part.toLowerCase().replace(/[^a-z0-9가-힣]+/g, "");
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .join(" / ");
}

function cleanedNativeGloss(value?: string) {
  const normalized = (value || "").trim();
  if (!normalized) return "";
  const quoted = normalized.match(/'(.*?)'/)?.[1];
  if (
    normalized.includes("이 용어는 이 문맥에서") ||
    normalized.includes("이 표현은 문장에서") ||
    normalized.includes("라는 뜻으로 쓰입니다") ||
    normalized.includes("역할을 합니다")
  ) {
    return quoted || "";
  }
  return normalized;
}

function extractLiveCues(text: string, profile: UserProfile | null): LiveCue[] {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (!normalized) return [];

  type CueTemplate = Omit<LiveCue, "gloss"> & { glosses: Record<string, string> };
  const cueBank: CueTemplate[] = [
    cue("breakneck speed", "C1", "phrase", "매우 빠른 속도. 변화 속도를 강조할 때 쓰는 표현.", "extremely fast pace; used to emphasize speed of change."),
    cue("on the cusp of", "C1", "phrase", "막 ~하기 직전의 단계. 큰 변화가 곧 올 때 쓰는 표현.", "at the edge of an important change that is about to happen."),
    cue("pull this off", "B2", "phrase", "어려운 일을 해내다.", "to successfully do something difficult."),
    cue("set my heart on", "C1", "phrase", "~하기로 강하게 마음먹다.", "to become strongly determined to do or get something."),
    cue("in my opinion", "B1", "phrase", "내 생각에는. 개인 의견을 부드럽게 표시.", "marks a personal opinion."),
    cue("kind of", "B1", "phrase", "약간, 어느 정도. 말의 강도를 낮추는 구어 표현.", "softens a statement; roughly 'somewhat'."),
    cue("AGI", "C1", "term", "Artificial General Intelligence. 여러 일을 일반적으로 해결하는 인공지능.", "Artificial General Intelligence; AI with broad problem-solving ability."),
    cue("artificial general intelligence", "C1", "term", "범용 인공지능. 특정 task가 아니라 넓은 문제 해결 능력을 말함.", "AI with broad, general problem-solving ability rather than one narrow task."),
    cue("general intelligence", "C1", "term", "일반지능. 새로운 문제를 이해하고 풀 수 있는 넓은 지능.", "broad intelligence that can understand and solve novel problems."),
    cue("theoretical neuroscience", "C2", "term", "이론 신경과학. 뇌를 수학적/계산적 모델로 설명하는 분야.", "neuroscience using abstract, mathematical, or computational models."),
    cue("neuroscience", "B2", "term", "신경과학. 뇌와 신경계를 연구하는 분야.", "the study of the brain and nervous system."),
    cue("compute", "B2", "term", "연산 자원 또는 계산 능력. AI 문맥에서는 GPU/TPU 같은 계산량을 뜻할 수 있음.", "computing power or resources, often GPU/TPU capacity in AI contexts."),
    cue("open-minded", "B2", "term", "열린 태도의. 새 의견을 받아들일 준비가 된 상태.", "willing to consider new ideas."),
    cue("inference", "C1", "term", "학습된 모델로 실제 답을 생성하는 단계.", "using a trained model to produce outputs."),
    cue("embedding", "C1", "term", "단어나 정보를 숫자 벡터로 표현한 것.", "a vector representation of a word, token, or object."),
    cue("attention", "B2", "term", "중요한 정보에 가중치를 두는 Transformer 핵심 메커니즘.", "a mechanism that weights relevant information in a sequence.")
  ];
  const minRank = minimumCueRank(profile?.target_level ?? "C1");
  const supportLanguage = profile?.support_language ?? "Korean";

  const found: LiveCue[] = [];
  for (const item of cueBank) {
    if (levelRank(item.level) < minRank) continue;
    const pattern = new RegExp(`\\b${escapeRegExp(item.text)}\\b`, "i");
    if (pattern.test(normalized)) {
      found.push({ text: item.text, level: item.level, kind: item.kind, gloss: localizedGloss(item.glosses, supportLanguage) });
    }
  }

  const fallbackStop = new Set([
    "answer",
    "answers",
    "question",
    "questions",
    "working",
    "people",
    "things",
    "something",
    "really",
    "because",
    "before",
    "after",
    "there",
    "their",
    "about",
    "would",
    "could",
    "should"
  ]);
  const fallbackWords = Array.from(normalized.matchAll(/\b[A-Za-z][A-Za-z-]{7,}\b/g))
    .map((match) => match[0])
    .filter((word) => !fallbackStop.has(word.toLowerCase()))
    .slice(0, 3)
    .map((word): LiveCue => ({
      text: word,
      gloss: "",
      level: "B2",
      kind: "term"
    }))
    .filter((cue) => levelRank(cue.level) >= minRank && minRank < levelRank("C2"));

  return dedupeCues([...found, ...fallbackWords]).slice(0, 6);
}

function extractSelectedLineItems(text: string, profile: UserProfile | null): LiveCue[] {
  const supportLanguage = profile?.support_language ?? "Korean";
  const cueItems = extractLiveCues(text, profile);
  const stop = new Set([
    "the",
    "and",
    "that",
    "this",
    "with",
    "from",
    "have",
    "what",
    "when",
    "where",
    "there",
    "about",
    "into",
    "your",
    "they",
    "them",
    "then",
    "just",
    "like",
    "really",
    "very",
    "yeah",
    "okay"
  ]);
  const words = Array.from(text.matchAll(/\b[A-Za-z][A-Za-z-]{3,}\b/g))
    .map((match) => match[0])
    .filter((word) => !stop.has(word.toLowerCase()))
    .filter((word, index, all) => all.findIndex((candidate) => candidate.toLowerCase() === word.toLowerCase()) === index)
    .slice(0, 8)
    .map((word): LiveCue => ({
      text: word,
      gloss: "",
      level: profile?.target_level === "C2" || profile?.target_level === "domain-heavy" ? "C1" : "B2",
      kind: "term"
    }));

  return dedupeCues([...cueItems, ...words]).slice(0, 10);
}

function cue(text: string, level: LiveCue["level"], kind: LiveCue["kind"], korean: string, english: string) {
  return { text, level, kind, glosses: { Korean: korean, English: english } };
}

function localizedGloss(glosses: Record<string, string>, supportLanguage: string) {
  const normalized = normalizeLanguageName(supportLanguage);
  if (glosses[normalized]) return glosses[normalized];
  const english = glosses.English ?? glosses.Korean ?? "";
  if (normalized === "English") return english;
  return `Explanation language: ${normalized}. ${english}`;
}

function minimumCueRank(level: UserProfile["target_level"]) {
  if (level === "C2" || level === "domain-heavy") return levelRank("C1");
  if (level === "C1") return levelRank("B2");
  if (level === "B2") return levelRank("B1");
  return levelRank("B1");
}

function levelRank(level: LiveCue["level"]) {
  return { B1: 1, B2: 2, C1: 3, C2: 4 }[level];
}

function inferSubtitleLanguage(name: string) {
  const lower = name.toLowerCase();
  for (const language of LANGUAGE_OPTIONS) {
    const namePattern = language.name.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const codePattern = language.code.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    if (new RegExp(`(^|[._ -])(${codePattern}|${namePattern})([._ -]|$)`).test(lower)) return language.code;
  }
  if (/(^|[._ -])(kor|korean|한국어)([._ -]|$)/.test(lower)) return "ko";
  if (/(^|[._ -])(eng|english)([._ -]|$)/.test(lower)) return "en";
  if (/(^|[._ -])(jpn|japanese)([._ -]|$)/.test(lower)) return "ja";
  if (/(^|[._ -])(zho|chi|chinese)([._ -]|$)/.test(lower)) return "zh";
  return null;
}

function learningModeWarning(subtitleLanguage: string | null, profile: UserProfile | null) {
  if (!subtitleLanguage || !profile) return null;
  const subtitleName = languageNameFromCode(subtitleLanguage);
  if (!subtitleName) return null;
  const support = normalizeLanguageName(profile.support_language);
  if (subtitleName !== support) return null;
  return `The loaded subtitles are already in your explanation language (${support}). For learning mode, load subtitles in the language you want to learn, then keep the explanation language different.`;
}

function languageNameFromCode(code: string | null) {
  const normalized = (code || "").toLowerCase();
  const fromCatalog = LANGUAGE_OPTIONS.find((language) => language.code.toLowerCase() === normalized || language.name.toLowerCase() === normalized);
  if (fromCatalog) return fromCatalog.name;
  if (normalized === "kor" || normalized === "korean") return "Korean";
  if (normalized === "eng" || normalized === "english") return "English";
  if (normalized === "jpn" || normalized === "japanese") return "Japanese";
  if (normalized === "zho" || normalized === "chi" || normalized === "chinese") return "Chinese";
  return code;
}

function normalizeLanguageName(value: string) {
  const lower = value.toLowerCase();
  const exact = LANGUAGE_OPTIONS.find((language) => language.name.toLowerCase() === lower || language.code.toLowerCase() === lower);
  if (exact) return exact.name;
  const partial = LANGUAGE_OPTIONS.find((language) => lower.includes(language.name.toLowerCase()));
  if (partial) return partial.name;
  if (lower.includes("한국")) return "Korean";
  if (lower.includes("영어")) return "English";
  if (lower.includes("일본")) return "Japanese";
  if (lower.includes("중국")) return "Chinese";
  return value;
}

function dedupeCues(cues: LiveCue[]) {
  const seen = new Set<string>();
  return cues.filter((cue) => {
    const key = cue.text.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function sceneWindowText(transcript: TranscriptResponse | null, sceneKey: number) {
  if (!transcript) return "";
  const start = sceneKey * SCENE_WINDOW_SECONDS;
  const end = start + SCENE_WINDOW_SECONDS;
  return transcript.segments
    .filter((segment) => segment.start >= start && segment.start < end)
    .map((segment) => segment.text)
    .join("\n");
}

function currentCueText(transcript: TranscriptResponse | null, currentTime: number) {
  if (!transcript) return "";
  const start = Math.max(0, currentTime - 12);
  const end = currentTime + 28;
  return transcript.segments
    .filter((segment) => segment.end >= start && segment.start <= end)
    .map((segment) => segment.text)
    .join("\n");
}

function activeTranscriptSegment(transcript: TranscriptResponse | null, currentTime: number) {
  if (!transcript) return undefined;
  const active = transcript.segments
    .filter((segment) => currentTime >= segment.start && currentTime < segment.end)
    .sort((a, b) => b.start - a.start)[0];
  if (active) return active;
  return transcript.segments
    .filter((segment) => segment.start <= currentTime)
    .sort((a, b) => b.start - a.start)[0];
}

function recapText(transcript: TranscriptResponse, currentTime: number) {
  const range = recapRange(transcript, currentTime);
  const blockSeconds = 15 * 60;
  const chunks: string[] = [];
  for (let start = range.start; start < range.end; start += blockSeconds) {
    const end = Math.min(start + blockSeconds, range.end);
    const lines = transcript.segments
      .filter((segment) => segment.start >= start && segment.start < end)
      .map((segment) => segment.text)
      .join("\n");
    if (lines.trim()) chunks.push(`[${formatTime(start)}-${formatTime(end)}]\n${lines}`);
  }
  return chunks.join("\n\n");
}

function recapRange(transcript: TranscriptResponse, currentTime: number) {
  const documentEnd = transcript.segments.at(-1)?.end ?? 15 * 60;
  const end = currentTime > 60 ? Math.min(currentTime, documentEnd) : Math.min(15 * 60, documentEnd);
  const start = Math.max(0, Math.floor(Math.max(0, end - 45 * 60) / (15 * 60)) * 15 * 60);
  return { start, end };
}

function formatRecapRange(transcript: TranscriptResponse, currentTime: number) {
  const range = recapRange(transcript, currentTime);
  return `${formatTime(range.start)}-${formatTime(range.end)}`;
}

function EmptyPlayer({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="flex h-full items-center justify-center text-sm font-semibold text-white">
      <div className="px-6 text-center">
        <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-white/10">
          <Play size={18} />
        </div>
        <p className="mt-3">{title}</p>
        <p className="mt-1 text-xs font-medium text-white/70">{detail}</p>
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

function extractYouTubeStartSeconds(url: string) {
  try {
    const parsed = new URL(url);
    return parseYouTubeTime(parsed.searchParams.get("t") || parsed.searchParams.get("start"));
  } catch {
    return 0;
  }
}

function parseYouTubeTime(value: string | null) {
  if (!value) return 0;
  const normalized = value.trim().toLowerCase();
  if (/^\d+$/.test(normalized)) return Number(normalized);
  const match = normalized.match(/^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s?)?$/);
  if (!match) return 0;
  return Number(match[1] || 0) * 3600 + Number(match[2] || 0) * 60 + Number(match[3] || 0);
}

function formatTime(seconds: number) {
  const total = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const rest = total % 60;
  if (hours) return `${hours}:${minutes.toString().padStart(2, "0")}:${rest.toString().padStart(2, "0")}`;
  return `${minutes}:${rest.toString().padStart(2, "0")}`;
}
