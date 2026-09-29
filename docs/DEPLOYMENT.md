# Deployment

## Deployment Status

The existing deployment instructions below describe the demo design, not proof
that each cloud resource is still running. The September 2026 Linux audit
validated an isolated mock API; it did not migrate production or model inference.
See [Linux development and operations](#linux-development-and-operations) for
the compatibility matrix, repeatable commands, results, and remaining gates.

## Existing Demo Recommendation

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

## Linux Development and Operations

### Scope and Component Inventory

Audit date: 2026-09-29. Code baseline: `099e925a01d3bd8f5678b6c53c10420e2d7b7677`.
Public docs omit host addresses, personal absolute paths, credentials, and raw
operational logs. The operator handoff is kept outside tracked files.

| Component | Observed state | Decision and evidence |
| --- | --- | --- |
| FastAPI, Pydantic, SQLAlchemy, SQLite | Existing Mac listener returned `/health`; independent Linux mock API exercised | Linux development and isolated operation verified. `backend/app/main.py`, `db/session.py`, `api/routes_documents.py`; real inference is a separate gate. |
| Next.js UI and server proxy | Linux production build verified; Vercel configuration documented | Linux development possible; retain existing cloud placement if deployed. `frontend/package.json`, `app/api/backend/[...path]/route.ts`. Cloud deployment/account state not inspected. |
| MLX/Gemma | Mac backend process observed; no inference requested during this audit | Keep on Apple Silicon Mac. `backend/requirements-mlx.txt`, `app/llm/mlx_adapter.py`, `scripts/setup_backend_mlx.sh`. Process/health is not inference-quality evidence. |
| PDF/DOCX ingestion and normalization | Platform-independent tests run on Linux | Linux possible. `document_ingestion_service.py`, `document_section_service.py`; external PDF corpus evaluation remains unverified. |
| Local video/subtitles | File APIs and subtitle parsing implemented; test coverage available | Linux possible after choosing a curated library and validating browser codecs. `local_media_service.py` uses filesystem paths, not macOS APIs. Keep disabled in shared demos. No media copied. |
| YouTube transcript fetching | HTTP integration and cache implemented | Platform-independent, but external functionality unverified. `video_transcript_service.py`, `requirements.txt`; network restrictions and upstream changes remain separate checks. |
| Remote Gemma / GGUF bridge | Code and launcher present, no Linux model service activated | Possible after changes and benchmarking. `remote_gemma_adapter.py` expects `/generate` returning `text`, not the raw OpenAI API. `thinkpad_gemma4_q4_server.py` bridges llama.cpp; `LLAMA_SERVER` defaults to a Homebrew path and must be an existing absolute Linux binary path. |
| Ollama | Adapter present, no daemon verified | Defer runtime decision. `ollama_adapter.py` falls back to mock on failure, so a successful response alone does not prove real inference. |
| Render backend | `render.yaml`, `backend/Dockerfile` only | Retain existing cloud deployment if present; live status unverified. Dockerfile uses Python 3.11 while tests target 3.12. Image not built in this audit. |
| Funnel and launchd supervisors | Mac launcher changes are uncommitted operator work | Keep Mac services untouched. `scripts/run_funnel_backend.sh`; untracked launchd scripts are not part of the Linux branch. Funnel/public routing state not independently verified. |
| Benchmarks, paper experiments, monitoring scripts | Research/one-shot scripts | Run on demand. `model_benchmark.py`, `page_batch_experiment.py`, `monitor_gemma4_server.py`; no evidence these need a new persistent Linux service. |

No Xcode, iOS signing, Keychain, or Docker socket dependency was found in the
application paths above. MLX/Metal and launchd are the concrete Mac dependencies.
No Compose, privileged container, or Buildx requirement was found for normal API
execution. This is not a claim that every experimental script is portable.

### Runtime Decision

Use the supplied **user systemd service for isolated mock validation**. The API
already runs as a Python process, so a container daemon is not required.
`deploy/systemd/gemmalens-api.service` binds only `127.0.0.1:18012`, uses a
test-only key, one worker, separate state, and disables model switching/media.

Podman/Quadlet was absent on the inspected host. Docker/Compose/Buildx clients
were present, but the daemon/socket units had failed and the user could not
access the socket. Running kernel and installed module versions differed;
Docker logs reported bridge creation unsupported. Reboot remediation was not
performed and causality was not conclusively established. Host repair, Podman
installation, user/group changes, firewall edits, and global logging policy
belong to the infrastructure owner. No Quadlet compatibility is claimed.

Keep Vercel placement and Mac inference until there is a tested reason to change
them. Do not run an additional production data writer against the same dataset.
Services sharing a Unix user are not strongly isolated from one another.

### Development Setup

Verified Linux tools: Python 3.12.14 and Node 22.23.0. The noninteractive shell
instead selected Python 3.14.7 and Node 26.10.0, so select versions explicitly.
Rust 1.97.1, Flutter 3.44.7, and Codex CLI 0.157.1 were observed but are not
GemmaLens dependencies. Python requirements are ranges, not a lockfile; record
`pip freeze` for each release. `npm ci` uses the committed frontend lockfile.

Use a new local clone on Linux, never a shared Mac working directory. From that
clone, with Python 3.12 and Node 22 selected:

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
cd backend
.venv/bin/python -m pytest -q -rs
.venv/bin/ruff check app tests
cd ../frontend
npm ci
npm run build
```

For terminal development, start the API in one terminal:

```bash
cd backend
APP_DEMO_MODE=true MODEL_PROVIDER=mock MODEL_SWITCHING_ENABLED=false \
  LOCAL_MEDIA_LIBRARY_ENABLED=false \
  .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 18012
```

Then start the frontend in another terminal:

```bash
cd frontend
BACKEND_INTERNAL_URL=http://127.0.0.1:18012 \
  npm run dev -- --hostname 127.0.0.1 --port 13003
```

These commands create disposable development state in the backend directory.
Use the systemd recipe below for state outside Git and API authentication. Do
not use `run_local_stack.sh` for coexistence testing: it kills listeners on its
configured ports and selects MLX. Never run pytest from a live service working
directory: its fixtures delete `model_runtime.json` and initialize a local DB.

External corpus evaluation is opt-in and is not counted as passed when skipped:

```bash
cd backend
GEMMALENS_EVAL_PAPERS_DIR=/path/to/authorized/eval_papers \
  .venv/bin/python -m pytest -q tests/test_learning_output_matrix.py
```

Required files: `attention_is_all_you_need.pdf`, `batch_norm.pdf`, `bert.pdf`.
An explicitly configured but incomplete corpus fails rather than skips.
Do not download or publish source PDFs without checking redistribution rights.

### Isolated User Service

Prerequisites: a working user systemd manager, Python venv above, `openssl`, an
unused port 18012, and no existing GemmaLens user-service paths. The setup script
refuses existing paths. It creates configuration but does not enable or start
the service. Invoke it from the intended clone:

```bash
bash scripts/setup_linux_validation.sh
systemctl --user start gemmalens-api.service
curl --fail http://127.0.0.1:18012/health
set -a
. "$HOME/.config/gemmalens/api.env"
set +a
backend/.venv/bin/python scripts/linux_mock_smoke.py
unset BACKEND_API_KEY CORS_ORIGINS
systemctl --user stop gemmalens-api.service
systemctl --user is-enabled gemmalens-api.service
```

`disabled` after validation is intentional. The generated key is random and
stored with mode 0600, not displayed or committed. This environment file is
trusted local configuration; do not source untrusted files. The smoke uses only
the fixed loopback validation port, checks mock mode before writes, and creates
then deletes its own document and dictionary item. Use a fresh validation DB.

The unit reads code through `~/.local/share/gemmalens/current`, a symlink to the
clone. State lives in `~/.local/state/gemmalens/`; credentials live separately in
`~/.config/gemmalens/api.env`. No model download occurs. The main settings are:

| Setting | Purpose |
| --- | --- |
| `APP_DEMO_MODE`, `MODEL_PROVIDER` | Both `true` and `mock` are required for mock; `ModelRuntimeService._merged_config` otherwise chooses MLX. |
| `MODEL_SWITCHING_ENABLED` | Keep false for shared validation; persisted runtime JSON can override environment selections, so use fresh state. |
| `DATABASE_URL` | Absolute SQLite URL; unit uses separate state, never the Mac DB. |
| `UPLOAD_STORAGE_DIR`, `TRANSCRIPT_CACHE_DIR` | Uploaded sources and derived transcript cache. |
| `MODEL_RUNTIME_CONFIG_PATH` | Persistent model selection; keep isolated from tests and Mac runtime. |
| `BACKEND_API_KEY` | Server secret; health and existing public upload/file routes are exceptions, so API key alone is not a public-access policy. |
| `BACKEND_INTERNAL_URL`, `GEMMALENS_API_KEY` | Next.js server-side proxy configuration. Never use a `NEXT_PUBLIC_*` secret. |
| `LOCAL_MEDIA_LIBRARY_ENABLED`, `LOCAL_VIDEO_LIBRARY_DIR` | Disabled by default; enable only with a curated directory and separate review. |
| `REMOTE_GEMMA_BASE_URL`, `REMOTE_GEMMA_MODEL`, `MLX_MODEL_PATH` | Real inference configuration, not used in mock validation. |
| `RAW_MODEL_OUTPUT_PATH` | Optional sensitive debug output; unset for the service. |

Resource limits: CPU 200% (two cores), memory high 1.5 GiB/max 2 GiB, 128 tasks,
one worker, restart on failure with a three-start/60-second limit. SIGTERM allows
30 seconds of application shutdown within systemd's 45-second stop timeout.
These are mock API limits, not an inference capacity claim. Model/CPU inference
latency and peak RSS must be measured separately before selecting that runtime.

No network-online dependency is needed for loopback mock execution. systemd
process state is not readiness: `/health` checks liveness, and the smoke exercises
functionality. There is no automatic recovery from a hung-but-running worker;
an external health monitor remains an operations gate. Logs go to journald,
rate-limited to 200 messages/30 seconds; this does not cap journal disk usage.
Per-host journal retention/size limits require infrastructure coordination.

```bash
systemctl --user status gemmalens-api.service
journalctl --user -u gemmalens-api.service -n 100 --no-pager
systemctl --user show gemmalens-api.service -p MemoryCurrent -p NRestarts -p Result
du -sh "$HOME/.local/state/gemmalens" frontend/.next frontend/node_modules
df -h "$HOME"
```

The observed clone, venv, frontend dependencies/build occupied about 975 MiB;
the Playwright browser cache added about 641 MiB. Initial validation state was
64 KiB. Upload/cache/log retention has no application-wide quota. Check growth
and free space before builds; keep model weights and bulk evaluation artifacts
off this preparation path. The planned disk expansion is not assumed complete.

After a separately approved operating plan, enable the dedicated service with
`systemctl --user enable --now gemmalens-api.service`. Boot operation also needs
user lingering (`loginctl show-user "$USER" -p Linger`); it was already enabled
on the audited host. Changing linger is a host-owner action. Boot/reboot behavior
was not tested. Do not expose this validation unit as the production service.

### Backup, Restore, Update, and Rollback

SQLite contains documents, analyses, dictionary and profile data. Original
uploads are separate files. `DocumentIngestionService.save_original_file`
stores absolute paths, so copying the DB alone or changing its directory does
not relocate source files. Runtime JSON stores provider choices. Browser-local
quiz/review drafts are not part of a server DB backup. Media libraries/models
are separate operator-managed datasets.

For a coherent backup of the isolated instance, stop only its service, archive
the complete state directory with mode 0600 under a private backup directory,
and restart if it was previously active. Example after choosing a fresh archive
name; never run this against production without its transition approval:

```bash
umask 077
mkdir -p "$HOME/.local/share/gemmalens/backups"
systemctl --user stop gemmalens-api.service
tar -C "$HOME/.local/state" -czf \
  "$HOME/.local/share/gemmalens/backups/state-$(date -u +%Y%m%dT%H%M%SZ).tgz" gemmalens
```

Store a separately encrypted copy of configuration/keys under the operator's
secret-backup policy. Do not put secrets in the state archive or Git. Preserve
the deployed commit and Python dependency snapshot with backup metadata. No
off-host backup destination, schedule, retention, or encryption key was selected
in this audit; define and exercise them before persistent operation.

Restore into a fresh staging directory first, run SQLite `PRAGMA integrity_check`
using Python's `sqlite3`, and verify source-file bytes. Restore service state to
the same absolute path while stopped, retaining the old directory for rollback.
Cross-host restore needs an explicit mapping for `documents.original_file_path`
and local-media paths; test that mapping on a copy, including original-file API
retrieval, before changing the production writer. The audit verified archive
extraction, DB integrity, source bytes and restart persistence on synthetic data;
it did not perform a production restore or a cross-host path migration.

For updates, build/test a new independent checkout with its own venv; record its
commit and dependency snapshot. Stop the dedicated service, back up state, and
point `current` at the tested checkout before starting and running the smoke on
disposable state. Do not run regression tests against production state.
`db/init_db.py` applies startup schema changes; reverting code alone may not
revert data/schema. If no new writes occurred, restore the matching snapshot and
old checkout. After any new writes, first preserve the new DB/uploads and audit
records, then reconcile them before selecting a rollback dataset. Never silently
discard post-cutover data.

### Validation and Handoff Gates

The Linux baseline build completed. After two test-harness corrections, backend
tests report **152 passed, 1 external-corpus evaluation skipped**. The original
baseline had 151 passed/2 failed: a stale dictionary deletion assertion and an
unavailable local PDF corpus. Changed test files and the new smoke pass Ruff.
The full baseline Ruff check had 26 findings; fixing the touched test's import
order removes one, with 25 remaining existing findings still blocking a clean
CI lint gate. No broad formatting rewrite was performed.

The existing Chromium `video.spec.ts` and `internal-tools.spec.ts` suite reported
**3 passed, 7 failed**, including when connected to the authenticated mock API.
The failures include missing UI expectations and incomplete mock-document routes;
their root causes are not fully diagnosed. A first run without backend wiring
also failed and is not used as proof of application behavior. The ad-hoc
`screenshot.spec.ts` was excluded because it hardcodes another port and a local
document ID. Browser acceptance is therefore an open gate, not a passing check.

To reproduce the connected suite after starting the isolated API:

```bash
set -a
. "$HOME/.config/gemmalens/api.env"
set +a
export GEMMALENS_API_KEY="$BACKEND_API_KEY"
export BACKEND_INTERNAL_URL=http://127.0.0.1:18012
export PLAYWRIGHT_BASE_URL=http://127.0.0.1:13003
cd frontend
npx playwright install chromium
npx playwright test tests/e2e/video.spec.ts tests/e2e/internal-tools.spec.ts --workers=2
```

Use Node 22, an unused frontend port, and the dedicated validation dataset.
Playwright's config can reuse a pre-existing server; verify ownership first.
Afterward stop the dedicated API and unset the exported key variables.

Systemd verification, authenticated mock API workflow, upload/read after restart,
graceful stop, and staged archive integrity checks passed. Service was left
inactive and disabled. Compilation, startup, and functional checks are separate
evidence; none demonstrates actual Gemma inference or public cloud health.

A production-mode Next.js process also returned homepage HTTP 200 and forwarded
an authenticated model-status request through `/api/backend/*` to the isolated
mock API. The key was absent from the returned homepage HTML. This limited proxy
smoke does not override the failed browser acceptance tests or prove that every
client asset is free of secrets.

`npm audit` reported 11 findings (1 critical, 7 high, 1 moderate, 2 low) against
the existing lockfile. Direct dependencies reported include Next.js (critical),
pdfjs-dist and postcss (high). Validate patched compatible versions and rerun
build/browser tests before any public deployment. No `audit fix --force` applied.

The Linux Codex handoff must identify the exact commit, independent checkout,
version-selection commands, current service state, test outcomes, and blockers.
Continue from Git commits, not copied account tokens or a transferred running
Codex conversation. Mac follow-up is real MLX load/inference with authorized
sample documents on an independent worktree; share commit, model/runtime version,
latency/RSS, and sanitized outcomes. If Mac is offline, mark that gate pending.

Work branch: `chore/linux-readiness-20260929`, based on upstream `main`. Test
harness correction: `871d332`; service preparation: `46545e1`. The Mac local main
and upstream main had 257 commits on each side but identical tip trees and no
unmatched patches in `git log --left-right --cherry-pick`. Tip author/committer
metadata differed; the rewriting mechanism was not established. A fresh upstream
worktree preserves both histories and uncommitted operator work. Do not force
push, reset the original checkout, or treat that divergence as new source work.

Production cutover remains **not performed**. Before approval, resolve dependency
and lint gates, validate real inference and a full restore, establish monitoring
and storage/log retention, and specify the single writer, final synchronization,
traffic switch, success checks, and rollback data reconciliation. Host reboot,
Docker repair, public DNS/Tunnel changes, and existing service replacement are
outside the completed isolated validation.
