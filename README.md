# IPL Crowd Dynamics and Agentic Orchestration System

Real-time crowd management prototype for IPL stadium operations. The app combines a FastAPI backend, a React/Vite dashboard, local resilience fallbacks, and optional Google Cloud integrations for Firestore, BigQuery, Pub/Sub, Maps, Gemini, and Cloud Run.

## What Is Included

- FastAPI backend for telemetry, gate status, evacuation, agent dispatch, and field reports.
- React 19 dashboard for live crowd status, reports, evacuation overlays, and admin controls.
- EvacuNet hazard assessment model using PyTorch.
- Gemini-powered orchestration tools with manual approval required for sensitive actions.
- Local development fallbacks when Firestore, BigQuery, Gemini, or Maps credentials are missing.
- Docker Compose for running backend and frontend together.
- Cloud Run deployment shortcut with Secret Manager wiring and pre-deploy secret scanning.

## Repository Layout

```text
ipl-crowd-management/
  backend/
    app/
      agents/          Gemini orchestration and sub-agents
      core/            security, rate limits, physics, EvacuNet
      models/          Pydantic request/response models
      routes/          FastAPI routers
      services/        Firestore, BigQuery, Pub/Sub, Maps adapters
      config.py        environment-based settings
      main.py          FastAPI app entrypoint
    pipeline/          Apache Beam/Dataflow pipeline
    tests/             backend tests
    .env.example       backend environment template
    Dockerfile
    requirements.txt
  frontend/
    src/
      components/
      hooks/
      services/
      utils/
    package.json
    vite.config.js
  scripts/
    secret_scan.ps1
  deploy_shortcut.ps1
  docker-compose.yml
  firestore.rules
```

## Prerequisites

- Python 3.11 or newer.
- Node.js 20 or newer.
- Docker Desktop, for container and Compose checks.
- Google Cloud CLI, only for deployment.
- A Google Cloud project, only for live Firestore, BigQuery, Pub/Sub, Gemini, Maps, or Cloud Run usage.

## Backend Setup

From the repository root:

```powershell
Copy-Item backend/.env.example backend/.env
```

Edit `backend/.env` and set at least:

```text
ADMIN_API_KEY=<strong-local-admin-key>
```

For a local key in PowerShell:

```powershell
[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLower()
```

Then install and run:

```powershell
cd backend
python -m pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

The backend is available at `http://localhost:8000`. Health check:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
```

## Frontend Setup

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

The dashboard is available at `http://localhost:5173`.

During local Vite development, the frontend uses `API_BASE_URL=/api`, and `frontend/vite.config.js` proxies `/api` to `http://localhost:8000`. For deployed/static builds, set:

```text
VITE_BACKEND_URL=https://your-backend-url
```

Trailing slashes are removed automatically by `frontend/src/utils/constants.js`.

## Admin API Key

Protected endpoints require the `X-API-Key` header to match `ADMIN_API_KEY`.

Examples of protected endpoints:

- `POST /gates/{gate_id}/signage`
- `POST /evacuation/assess`
- `POST /evacuation/trigger`
- Admin-oriented agent actions exposed by backend routes

The frontend stores the key in browser `sessionStorage` after the user enters it. Do not commit real keys. In production, the backend refuses to start without `ADMIN_API_KEY`.

## Environment Variables

Backend variables are loaded from environment variables and `backend/.env` in local development.

| Variable | Required locally | Required in production | Notes |
| --- | --- | --- | --- |
| `ADMIN_API_KEY` | Yes for protected endpoints | Yes | Strong shared admin key for protected APIs. |
| `APP_ENV` | No | Yes | Use `development`, `test`, or `production`. |
| `LOG_LEVEL` | No | No | Defaults to `INFO`. |
| `CORS_ORIGINS` | No | Yes | Comma-separated frontend origins. No wildcard in production. |
| `GOOGLE_CLOUD_PROJECT` | No for fallback mode | Yes for GCP services | Google Cloud project ID. |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | Optional on Cloud Run | Local ADC/service-account path when needed. |
| `GOOGLE_API_KEY` | No | Yes for Gemini | Missing locally makes orchestrator dispatch return an error response. |
| `GOOGLE_MAPS_API_KEY` | No | Yes for live Maps routes | Missing locally returns mock pedestrian routes. |
| `FIRESTORE_DATABASE` | No | No | Defaults to `(default)`. |
| `PUBSUB_TOPIC` | No | No | Defaults to `crowd-telemetry`. |
| `PUBSUB_SUBSCRIPTION` | No | No | Defaults to `crowd-telemetry-push`. |
| `BIGQUERY_DATASET` | No | No | Defaults to `crowd_analytics`. |
| `BIGQUERY_TABLE` | No | No | Defaults to `telemetry_events`. |
| `GCS_BUCKET` | No | No | Reserved for archive/storage flows. |
| `STADIUM_ID` | No | No | Defaults to `chinnaswamy_stadium`. |

Frontend variables:

| Variable | Required | Notes |
| --- | --- | --- |
| `VITE_BACKEND_URL` | Only for deployed/static frontend | Absolute backend URL. Local dev defaults to `/api`. |
| `VITE_FIREBASE_*` | No for prototype mode | Firebase config values if live Firebase listeners are enabled. |
| `VITE_USE_EMULATOR` | No | Set to `true` to use Firebase emulators where supported. |

## Local Fallback Behavior

When `APP_ENV` is not `production`:

- Firestore credential/API failures fall back to an in-memory store for gates, reports, strict protocol, and evacuation state.
- BigQuery credential/API failures disable local analytics writes and return empty query results.
- Google Maps routes fall back to mock route data if `GOOGLE_MAPS_API_KEY` is missing.
- Gemini orchestrator dispatch returns an error if `GOOGLE_API_KEY` is missing, but the app stays up.

When `APP_ENV=production`, Firestore and BigQuery credential failures are not silently swallowed.

## Docker

Build only the backend image:

```powershell
docker build -t ipl-backend:local ./backend
```

Run the backend container and check health:

```powershell
docker run --rm -p 8080:8080 -e APP_ENV=development -e ADMIN_API_KEY=local-dev-key ipl-backend:local
Invoke-WebRequest -UseBasicParsing http://localhost:8080/health
```

Run both services:

```powershell
Copy-Item backend/.env.example backend/.env
# Edit backend/.env and set ADMIN_API_KEY.
docker compose up -d --build
```

Then open:

- Backend: `http://localhost:8000/health`
- Frontend: `http://localhost:5173`

Stop the stack:

```powershell
docker compose down
```

## Tests And Checks

Backend:

```powershell
python -m pytest backend/tests -q
python -m ruff check backend
```

Frontend:

```powershell
cd frontend
npm run lint
npm run test
npm run build
```

Secret scan:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/secret_scan.ps1
```

The scanner checks tracked and untracked non-ignored files for common API keys, private keys, service-account material, and high-risk secret assignments.

## Deployment

Deployment is handled by `deploy_shortcut.ps1`.

Before first deployment, create these Google Secret Manager secrets in the configured project:

```powershell
"your-gemini-key" | gcloud secrets create GEMINI_API_KEY --data-file=- --project <project-id>
"your-maps-key" | gcloud secrets create MAPS_API_KEY --data-file=- --project <project-id>
"your-strong-admin-key" | gcloud secrets create ADMIN_API_KEY --data-file=- --project <project-id>
```

Then review the configuration block at the top of `deploy_shortcut.ps1`, especially:

- `$PROJECT_ID`
- `$REGION`
- `$STADIUM_ID`
- Firestore, Pub/Sub, BigQuery, and GCS names
- `$BACKEND_INITIAL_CORS`

Run:

```powershell
powershell -ExecutionPolicy Bypass -File deploy_shortcut.ps1
```

The deploy script:

- Runs `scripts/secret_scan.ps1` first.
- Enables required Google Cloud APIs.
- Deploys the backend to Cloud Run with explicit app env vars.
- Binds Gemini, Maps, and admin keys from Secret Manager.
- Deploys the frontend with `VITE_BACKEND_URL` set to the backend URL.
- Updates backend CORS to include the deployed frontend URL.

The backend Cloud Run service is publicly reachable so the browser frontend can call it. Admin actions are still protected by `ADMIN_API_KEY`.

## Key Rotation

If any key is exposed:

1. Disable or delete the exposed key in its provider console.
2. Create a replacement key.
3. Update Google Secret Manager or local `.env`.
4. Redeploy affected services.
5. Run `scripts/secret_scan.ps1` before committing.

## API Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Liveness probe. |
| `POST` | `/pubsub` | Pub/Sub push handler. |
| `POST` | `/telemetry` | Direct telemetry ingestion. |
| `GET` | `/gates` | All gate statuses. |
| `GET` | `/gates/{id}` | Single gate detail. |
| `POST` | `/gates/{id}/signage` | Update dynamic signage. Requires admin key. |
| `POST` | `/evacuation/assess` | Run EvacuNet assessment. Requires admin key. |
| `POST` | `/evacuation/trigger` | Force evacuation. Requires admin key. |
| `GET` | `/evacuation/status` | Current evacuation state. |
| `POST` | `/agents/dispatch` | Natural language agent command. |
| `GET` | `/agents/status` | Agent system status. |
| `POST` | `/reports` | Submit field report. |
| `GET` | `/reports` | Retrieve recent reports. |

## Known Limitations

- This is a prototype, not a certified life-safety system.
- The local Firestore fallback is in-memory and resets when the backend process stops.
- BigQuery analytics are skipped locally when credentials are unavailable.
- The WebSocket hook exists for future live updates, but the current backend does not expose a WebSocket endpoint.
- Some Firebase values in the frontend are demo defaults unless real `VITE_FIREBASE_*` values are provided.
- Cloud Run deployment requires real GCP credentials, enabled billing, and Secret Manager values.
- The backend image is large because it includes PyTorch and Apache Beam/Dataflow dependencies.

## License

MIT
