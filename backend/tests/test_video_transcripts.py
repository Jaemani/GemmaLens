SRT_SAMPLE = """1
00:00:01,000 --> 00:00:03,500
You're not gonna get away with this.

2
00:00:04,000 --> 00:00:06,000
I should have told you earlier.
"""

VTT_SAMPLE = """WEBVTT

00:00:01.000 --> 00:00:02.000
This changes everything.
"""


def test_parse_srt_transcript(client):
    response = client.post("/video/transcripts/parse", json={"content": SRT_SAMPLE, "source_name": "demo.srt"})

    assert response.status_code == 200
    body = response.json()
    assert body["source_type"] == "subtitle"
    assert body["source_id"] == "demo.srt"
    assert len(body["segments"]) == 2
    assert body["segments"][0]["start"] == 1.0
    assert body["segments"][0]["end"] == 3.5
    assert body["segments"][0]["text"] == "You're not gonna get away with this."
    assert "I should have told you earlier." in body["plain_text"]


def test_parse_vtt_transcript(client):
    response = client.post("/video/transcripts/parse", json={"content": VTT_SAMPLE, "source_name": "demo.vtt"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["segments"]) == 1
    assert body["segments"][0]["duration"] == 1.0


def test_invalid_subtitle_returns_400(client):
    response = client.post("/video/transcripts/parse", json={"content": "not subtitles", "source_name": "bad.txt"})

    assert response.status_code == 400


def test_invalid_youtube_url_returns_400(client):
    response = client.post("/video/transcripts/youtube", json={"url": "https://example.com/watch?v=abc"})

    assert response.status_code == 400
