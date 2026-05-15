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


def test_analysis_uses_profile_level_when_model_level_unknown(client):
    updated = client.patch("/profile", json={"target_level": "C2"})
    assert updated.status_code == 200
    created = client.post(
        "/documents",
        json={"title": "Short ML note", "content": "We introduce a new language representation model called BERT.", "source_type": "text"},
    )
    assert created.status_code == 200

    analyzed = client.post(f"/documents/{created.json()['id']}/analyze")
    assert analyzed.status_code == 200
    assert analyzed.json()["difficulty"]["overall_level"] == "C2"


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


def test_runtime_persisted_preset_applies_model_path(client):
    updated = client.post("/models/config", json={"preset_id": "gemma4-e2b-mlx"})
    assert updated.status_code == 200
    assert updated.json()["preset_id"] == "gemma4-e2b-mlx"
    assert "gemma-4-e2b" in updated.json()["mlx_model_path"]


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
    assert len(analysis["concepts"]) >= 1
    assert analysis["concepts"][0]["concept"]

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

    saved_concept = client.post(
        "/dictionary/items",
        json={
            "item_type": "concept",
            "text": analysis["concepts"][0]["concept"],
            "meaning": analysis["concepts"][0]["explanation"],
            "document_id": document["id"],
        },
    )
    assert saved_concept.status_code == 200

    items = client.get("/dictionary/items")
    assert items.status_code == 200
    assert len(items.json()) == 2
    term_item = next(item for item in items.json() if item["item_type"] == "term")
    assert term_item["view_count"] == 0

    viewed = client.post(f"/dictionary/items/{term_item['id']}/view")
    assert viewed.status_code == 200
    assert viewed.json()["view_count"] == 1
    assert viewed.json()["last_viewed_at"] is not None

    deleted = client.delete(f"/dictionary/items/{term_item['id']}")
    assert deleted.status_code == 204
    assert len(client.get("/dictionary/items").json()) == 1


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


def test_upload_docx_document_uses_ingestion_service(client):
    from io import BytesIO

    from docx import Document

    buffer = BytesIO()
    doc = Document()
    doc.add_paragraph("Batch Normalization stabilizes deep network training.")
    doc.add_table(rows=1, cols=2).rows[0].cells[0].text = "term"
    doc.tables[0].rows[0].cells[1].text = "meaning"
    doc.save(buffer)

    uploaded = client.post(
        "/documents/upload",
        files={
            "file": (
                "notes.docx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert uploaded.status_code == 200
    body = uploaded.json()
    assert body["title"] == "notes.docx"
    assert body["source_type"] == "docx"
    assert "Batch Normalization" in body["content"]
    assert "term | meaning" in body["content"]


def test_upload_legacy_doc_returns_actionable_error(client):
    uploaded = client.post(
        "/documents/upload",
        files={"file": ("legacy.doc", b"binary-doc-content", "application/msword")},
    )
    assert uploaded.status_code == 400
    assert ".doc files are not directly supported" in uploaded.json()["detail"]


def test_missing_resources_return_404(client):
    assert client.get("/documents/missing").status_code == 404
    assert client.get("/documents/missing/analysis").status_code == 404
    assert client.delete("/dictionary/items/missing").status_code == 404
