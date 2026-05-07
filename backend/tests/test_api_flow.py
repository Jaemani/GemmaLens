SAMPLE_TEXT = (
    "Although previous studies have suggested a correlation between sleep deprivation "
    "and reduced cognitive performance, the extent to which these findings generalize "
    "across real-world learning environments remains unclear. To address this gap, "
    "we analyze longitudinal study logs collected from undergraduate students over a "
    "six-week period."
)


def test_health_and_model_status(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    status = client.get("/models/status")
    assert status.status_code == 200
    body = status.json()
    assert body["mock_fallback"] is True
    assert "provider" in body
    assert "mlx_model_available" in body


def test_document_analysis_and_dictionary_flow(client):
    created = client.post(
        "/documents",
        json={"title": "Sleep study", "content": SAMPLE_TEXT, "source_type": "text"},
    )
    assert created.status_code == 200
    document = created.json()
    assert document["title"] == "Sleep study"

    listed = client.get("/documents")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == document["id"]

    analyzed = client.post(f"/documents/{document['id']}/analyze")
    assert analyzed.status_code == 200
    analysis = analyzed.json()
    assert analysis["document_id"] == document["id"]
    assert analysis["domain"]["primary_domain"]
    assert {term["term"] for term in analysis["terms"]} >= {
        "sleep deprivation",
        "cognitive performance",
        "longitudinal study",
    }

    saved = client.post(
        "/dictionary/items",
        json={
            "item_type": "term",
            "text": "sleep deprivation",
            "meaning": "not getting enough sleep",
            "document_id": document["id"],
        },
    )
    assert saved.status_code == 200
    assert saved.json()["encounter_count"] == 1

    saved_again = client.post(
        "/dictionary/items",
        json={
            "item_type": "term",
            "text": "sleep deprivation",
            "meaning": "lack of sufficient sleep",
            "document_id": document["id"],
        },
    )
    assert saved_again.status_code == 200
    assert saved_again.json()["encounter_count"] == 2

    items = client.get("/dictionary/items")
    assert items.status_code == 200
    assert len(items.json()) == 1

    deleted = client.delete(f"/dictionary/items/{saved_again.json()['id']}")
    assert deleted.status_code == 204
    assert client.get("/dictionary/items").json() == []


def test_upload_document_uses_ingestion_service(client):
    uploaded = client.post(
        "/documents/upload",
        files={"file": ("notes.md", b"# Methods\n\nWe analyze longitudinal study logs.", "text/markdown")},
    )
    assert uploaded.status_code == 200
    body = uploaded.json()
    assert body["title"] == "notes.md"
    assert body["source_type"] == "markdown"
    assert "longitudinal study logs" in body["content"]

    empty = client.post(
        "/documents/upload",
        files={"file": ("empty.txt", b"\n\n", "text/plain")},
    )
    assert empty.status_code == 400


def test_missing_resources_return_404(client):
    assert client.get("/documents/missing").status_code == 404
    assert client.get("/documents/missing/analysis").status_code == 404
    assert client.delete("/dictionary/items/missing").status_code == 404
