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

PERSONA_SUBTITLES = [
    (
        "movie_dialogue",
        """1
00:00:01,000 --> 00:00:03,500
You're not gonna get away with this.

2
00:00:04,000 --> 00:00:06,200
I should have told you earlier.
""",
        "You're not gonna get away with this.",
    ),
    (
        "technical_tutorial",
        """1
00:00:01,000 --> 00:00:04,000
Before we deploy the migration, we need to run an idempotent preflight check.

2
00:00:04,500 --> 00:00:08,000
Otherwise, stale metadata can propagate across worker nodes.
""",
        "idempotent preflight check",
    ),
    (
        "academic_lecture",
        """WEBVTT

00:00:01.000 --> 00:00:05.000
Today we are going to examine whether laboratory findings generalize to real-world learning environments.

00:00:05.500 --> 00:00:09.000
The key limitation is that controlled experiments often remove the very context we care about.
""",
        "laboratory findings generalize",
    ),
]


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


def test_persona_subtitle_scenarios_parse_to_plain_text(client):
    for source_name, content, expected_text in PERSONA_SUBTITLES:
        response = client.post("/video/transcripts/parse", json={"content": content, "source_name": source_name})

        assert response.status_code == 200
        body = response.json()
        assert len(body["segments"]) >= 2
        assert expected_text in body["plain_text"]
        assert all(segment["start"] < segment["end"] for segment in body["segments"])
