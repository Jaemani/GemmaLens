# Deployment

## Current Recommendation

Use Vercel for the frontend and keep the real FastAPI/Gemma backend on a local
machine exposed through Tailscale Funnel for demos. Protect the backend with a
shared API key and let the Vercel frontend call it through the same-origin
`/api/backend/*` proxy.

This avoids putting the API key in browser JavaScript and avoids most CORS/PDF
viewer failures.

```txt
Browser -> Vercel frontend -> /api/backend/* proxy -> Tailscale Funnel -> local FastAPI
```

For the public judging demo, the model host is a personal Mac running local
Gemma 4. This is intentionally temporary. The Mac backend should remain online
only for the judging window and should be shut down afterward.

## Vercel + Tailscale Funnel Backend

On the local backend machine:

```bash
export BACKEND_API_KEY="use-a-long-random-demo-key"
./scripts/run_funnel_backend.sh
```

Expose the backend through Tailscale Funnel:

```bash
tailscale funnel 8012
```

Use the HTTPS URL printed by Tailscale as the backend URL.

On Vercel, set:

```txt
BACKEND_INTERNAL_URL=https://YOUR-MACHINE.YOUR-TAILNET.ts.net
GEMMALENS_API_KEY=use-a-long-random-demo-key
```

Do not set `NEXT_PUBLIC_GEMMALENS_API_KEY` for this recommended setup. The
server-side proxy attaches `GEMMALENS_API_KEY` when forwarding requests.

Security checklist for this mode:

- Use a demo-only `BACKEND_API_KEY`; rotate it after judging.
- Use the Vercel server-side proxy. Do not expose the key through
  `NEXT_PUBLIC_GEMMALENS_API_KEY`.
- Keep the backend bound to the demo API only; do not expose SSH, file sharing,
  local databases, model directories, or arbitrary filesystem routes.
- Store demo uploads in the temporary SQLite/database path created by
  `scripts/run_funnel_backend.sh`.
- Use Tailscale Funnel only for the backend port needed by the demo.
- Keep `LOCAL_MEDIA_LIBRARY_ENABLED=false` for public judging unless you point
  `LOCAL_VIDEO_LIBRARY_DIR` at a curated demo-only folder. This prevents the
  public demo from listing or serving the Mac's broader `~/Movies` library.
- Shut down Funnel and the backend after judging.
- Do not commit private PDFs, videos, transcripts, model weights, runtime JSON,
  SQLite databases, or raw evaluation outputs.

### Direct Browser Mode

Only use this for quick internal testing:

```txt
NEXT_PUBLIC_API_BASE_URL=https://YOUR-MACHINE.YOUR-TAILNET.ts.net
NEXT_PUBLIC_GEMMALENS_API_KEY=use-a-long-random-demo-key
```

This exposes the key to the browser bundle. It is acceptable for a temporary
demo key, but the proxy mode above is safer.

## Older Cloud Mock Backend Option

Use Vercel for the frontend and a model-free FastAPI backend for team testing.

This gives the team a real shared flow:

- create document
- run analysis
- open structured result
- save dictionary items

The deployed backend should run `MockModelAdapter`. Real Gemma analysis stays local until the runtime path is decided.

## Backend On Render

The repo includes `render.yaml` and `backend/Dockerfile`.

Render settings:

- Blueprint file: `render.yaml`
- Service: `gemmalens-api`
- Runtime: Docker
- Health check: `/health`
- Disk: `/data`

Important environment values:

```txt
MODEL_PROVIDER=mock
MODEL_SWITCHING_ENABLED=false
MODEL_RUNTIME_CONFIG_PATH=/tmp/model_runtime.json
DATABASE_URL=sqlite:////data/gemmalens.db
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
- optional larger MLX 4-bit presets: local folders under `~/Models/mlx`
- optional GGUF bridge: local llama.cpp wrapper on `localhost:11445`
- `ollama`: local or LAN runtime
- future `android-local`: device-managed model download and inference
- future `hosted`: controlled cloud fallback

Do not expose a personal Mac LLM server directly to team testers. For local demos, use the Mac backend on a trusted network only, or package the runtime later.

## Local Model Hardening

Real model output must pass through:

```txt
raw model text -> JSON extraction/repair -> schema validation -> normalization -> quality warnings -> UI-safe result
```

The backend now normalizes common E4B issues such as typo enum values, missing fields, duplicate items, wrong source sentences, and low-confidence items. Use `scripts/local_model_smoke.py` for repeatable local checks.
