from app.main import settings


def test_backend_api_key_is_optional(client):
    original = settings.backend_api_key
    settings.backend_api_key = None
    try:
        response = client.get("/models/status")
        assert response.status_code == 200
    finally:
      settings.backend_api_key = original


def test_backend_api_key_blocks_non_public_routes(client):
    original = settings.backend_api_key
    settings.backend_api_key = "secret-demo-key"
    try:
        assert client.get("/health").status_code == 200
        assert client.get("/models/status").status_code == 401
        response = client.get("/models/status", headers={"x-gemmalens-api-key": "secret-demo-key"})
        assert response.status_code == 200
    finally:
        settings.backend_api_key = original
