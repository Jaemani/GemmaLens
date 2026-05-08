# Deployment

## Current Recommendation

Use Vercel for the frontend and a model-free FastAPI backend for team testing.

This gives the team a real shared flow:

- create document
- run analysis
- open structured result
- test A/B cleanup controls
- save dictionary items

The deployed backend should run `MockModelAdapter`. Real Gemma analysis stays local until the runtime path is decided.

## Backend On Render

The repo includes `render.yaml` and `backend/Dockerfile`.

Render settings:

- Blueprint file: `render.yaml`
- Service: `sololingo-api`
- Runtime: Docker
- Health check: `/health`
- Disk: `/data`

Important environment values:

```txt
MODEL_PROVIDER=mock
MODEL_SWITCHING_ENABLED=false
MODEL_RUNTIME_CONFIG_PATH=/tmp/model_runtime.json
DATABASE_URL=sqlite:////data/paperlens.db
CORS_ALLOW_ORIGIN_REGEX=https://.*\.vercel\.app
```

`MODEL_SWITCHING_ENABLED=false` keeps the deployed backend locked to mock mode. This prevents reviewers from selecting MLX/Ollama presets on a cloud server that has no local model.

## Frontend On Vercel

Set this Vercel environment variable:

```txt
NEXT_PUBLIC_API_BASE_URL=https://YOUR_RENDER_SERVICE.onrender.com
```

Then redeploy the frontend.

The frontend also keeps `/analysis/demo` as a no-backend fallback for UI review.

## Future Runtime Direction

Keep the current model adapter boundary:

- `mock`: shared UI/product testing
- `mlx`: local Mac runtime
- `ollama`: local or LAN runtime
- future `android-local`: device-managed model download and inference
- future `hosted`: controlled cloud fallback

Do not expose a personal Mac LLM server directly to team testers. For local demos, use the Mac backend on a trusted network only, or package the runtime later.
