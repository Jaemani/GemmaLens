import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.llm import get_model_adapter
from app.llm.mlx_adapter import MLXAdapter
from app.services import model_runtime_service


def test_default_runtime_does_not_select_a_personal_model(monkeypatch, tmp_path):
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    settings = Settings(app_demo_mode=False, model_runtime_config_path=str(tmp_path / "runtime.json"))
    monkeypatch.setattr(model_runtime_service, "get_settings", lambda: settings)
    status = model_runtime_service.ModelRuntimeService().status()
    assert status.provider == "unconfigured"
    assert status.preset_id == "unconfigured"
    with pytest.raises(HTTPException) as error:
        get_model_adapter()
    assert error.value.status_code == 503


def test_mock_without_demo_never_falls_back_to_mlx(monkeypatch, tmp_path):
    settings = Settings(model_provider="mock", app_demo_mode=False, model_runtime_config_path=str(tmp_path / "runtime.json"))
    monkeypatch.setattr(model_runtime_service, "get_settings", lambda: settings)
    assert model_runtime_service.ModelRuntimeService().status().provider == "unconfigured"


@pytest.mark.parametrize("task", ["terms", "phrases", "concepts", "sentences"])
def test_atomic_list_response_is_wrapped_without_loading_mlx(monkeypatch, task):
    adapter = object.__new__(MLXAdapter)
    monkeypatch.setattr(adapter, "_generate_prompt_output", lambda *args, **kwargs: '[{"value":"source-grounded"}]')
    result = adapter._json_task(task, "test prompt", 32, {})
    assert result == {task: [{"value": "source-grounded"}]}


def test_atomic_scalar_retries_then_uses_explicit_fallback(monkeypatch):
    adapter = object.__new__(MLXAdapter)
    calls = []

    def generate(*args, **kwargs):
        calls.append(args)
        return "true"

    monkeypatch.setattr(adapter, "_generate_prompt_output", generate)
    assert adapter._json_task("terms", "test prompt", 32, {"terms": []}) == {"terms": []}
    assert len(calls) == 2


def test_unconfigured_api_preserves_document_workflow_without_inference(client, monkeypatch, tmp_path):
    settings = Settings(model_provider="unconfigured", app_demo_mode=False, model_runtime_config_path=str(tmp_path / "runtime.json"))
    monkeypatch.setattr(model_runtime_service, "get_settings", lambda: settings)
    assert client.get("/models/status").json()["provider"] == "unconfigured"
    document = client.post("/documents", json={"title": "Portable", "content": "A source without a model.", "source_type": "text"})
    assert document.status_code == 200
    response = client.post(f"/documents/{document.json()['id']}/analyze")
    assert response.status_code == 503
    assert client.get(f"/documents/{document.json()['id']}").status_code == 200
