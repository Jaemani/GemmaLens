import httpx

from app.services.video_transcript_service import VideoTranscriptService


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_known_youtube_text_source_returns_segments_without_youtube_caption_api(monkeypatch, tmp_path):
    repeated = (
        "Mr. Clifford: So let's start with the basics. What is economics? "
        "Economics studies choices, scarce resources, opportunity cost, theories and graphs, "
        "and real world applications. "
    ) * 8
    html = f"""
    <html>
      <head><title>Intro to Economics</title></head>
      <body>
        <div id="transcript-view">
          <div class="section-content">{repeated}</div>
        </div>
      </body>
    </html>
    """

    def fake_get(*args, **kwargs):
        return _FakeResponse(html)

    monkeypatch.setattr(httpx, "get", fake_get)
    service = VideoTranscriptService()
    service.settings.transcript_cache_dir = str(tmp_path)

    result = service.fetch_youtube("https://www.youtube.com/watch?v=3ez10ADR_gM", ["en"])

    assert result.source_id == "3ez10ADR_gM"
    assert result.segments
    assert "scarce resources" in result.plain_text
    assert "known public transcript/article page" in (result.warning or "")


def test_parse_plain_timestamp_transcript():
    service = VideoTranscriptService()

    result = service.parse_subtitle(
        """
        00:00:00 hello guys welcome to my video
        00:00:02 about the Transformer
        00:00:05 recurrent neural networks existed before the Transformer
        """,
        "youtube-timestamp.txt",
    )

    assert len(result.segments) == 3
    assert result.segments[0].start == 0
    assert result.segments[0].end == 2
    assert "about the Transformer" in result.plain_text
