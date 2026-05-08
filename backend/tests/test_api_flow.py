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


def test_profile_language_settings(client):
    profile = client.get("/profile")
    assert profile.status_code == 200
    assert profile.json()["learning_language"] == "English"

    updated = client.patch(
        "/profile",
        json={
            "support_language": "Japanese",
            "learning_language": "Spanish",
            "target_level": "B2",
            "onboarding_completed": True,
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["support_language"] == "Japanese"
    assert body["learning_language"] == "Spanish"
    assert body["target_level"] == "B2"
    assert body["onboarding_completed"] is True


def test_model_config_can_switch_provider(client):
    updated = client.post(
        "/models/config",
        json={
            "provider": "mock",
            "ollama_model": "gemma4:test",
            "ollama_base_url": "http://localhost:11434",
            "mlx_model_path": "~/Models/mlx/gemma-4-e4b-it-OptiQ-4bit",
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["provider"] == "mock"
    assert body["ollama_model"] == "gemma4:test"

    status = client.get("/models/status")
    assert status.status_code == 200
    assert status.json()["ollama_model"] == "gemma4:test"


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
    assert "quality_warnings" in analysis
    assert {term["term"] for term in analysis["terms"]} >= {
        "sleep deprivation",
        "cognitive performance",
        "longitudinal study",
    }
    assert all("learning_priority" in term for term in analysis["terms"])

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
    assert items.json()[0]["view_count"] == 0

    viewed = client.post(f"/dictionary/items/{saved_again.json()['id']}/view")
    assert viewed.status_code == 200
    assert viewed.json()["view_count"] == 1
    assert viewed.json()["last_viewed_at"] is not None

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
