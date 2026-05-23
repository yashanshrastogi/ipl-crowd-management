# IPL Crowd Dynamics & Agentic Orchestration System

> Real-time crowd management platform for IPL stadiums, powered by GCP, Gemini AI, and the EvacuNet emergency subsystem.

![Status](https://img.shields.io/badge/status-prototype-blue)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![React](https://img.shields.io/badge/react-19-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Overview

An enterprise-grade, event-driven platform for monitoring and managing crowd dynamics at high-density IPL cricket matches. The system combines IoT sensor telemetry, computer-vision crowd density estimation, and Gemini-powered multi-agent orchestration to provide real-time safety decisions.

### Key Features

- **Real-Time Crowd Physics** — Pedestrian flow equations (Q = ρ·v·Wₑ) computed per gate
- **Multi-Agent Network** — Gemini-powered orchestrator, gate security, and routing agents
- **EvacuNet Emergency System** — PyTorch neural network for hazard probability assessment
- **Bento Dashboard** — React 19 glassmorphism UI with live sensor, gate, and map panels
- **GCP Integration** — Firestore (real-time state), Pub/Sub (telemetry), BigQuery (analytics)
- **Google Maps** — Gate markers, pedestrian routing, and walking path visualization

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Bento Dashboard                     │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────┐  │
│  │ Stadium  │ │ Density  │ │  Match   │ │   Crowdsourced     │  │
│  │   Map    │ │  Gauge   │ │   Day    │ │      Feed          │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┬───────────┘  │
│       └─────────────┴────────────┴────────────────┘              │
│                        Firestore Listeners                       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      FastAPI Backend (Cloud Run)                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐ │
│  │  Telemetry │ │   Gates    │ │ Evacuation │ │    Agents    │ │
│  │   Router   │ │   Router   │ │   Router   │ │    Router    │ │
│  └──────┬─────┘ └──────┬─────┘ └──────┬─────┘ └──────┬───────┘ │
│         │              │              │               │          │
│  ┌──────▼──────────────▼──────────────▼───────────────▼───────┐ │
│  │              Core Services Layer                            │ │
│  │  Crowd Physics │ EvacuNet │ Firestore │ BigQuery │ Maps    │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
ipl-crowd-management/
├── backend/
│   ├── app/
│   │   ├── agents/          # Gemini-powered multi-agent system
│   │   ├── core/            # Crowd physics, EvacuNet, thresholds
│   │   ├── models/          # Pydantic schemas
│   │   ├── routes/          # FastAPI routers
│   │   ├── services/        # GCP service integrations
│   │   ├── config.py        # Environment-based configuration
│   │   └── main.py          # FastAPI application entry
│   ├── pipeline/            # Apache Beam / Dataflow pipeline
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/      # React UI components (9 total)
│   │   ├── hooks/           # useFirestore, useWebSocket
│   │   ├── services/        # API client, Firebase SDK
│   │   ├── utils/           # Constants, crowd physics
│   │   ├── App.jsx          # Dashboard assembly
│   │   └── index.css        # Design system
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
└── README.md
```

## Quick Start

### Prerequisites

- **Python 3.11+** and **Node.js 20+**
- **Google Cloud** project with Firestore, Pub/Sub, BigQuery enabled
- API keys: `GOOGLE_API_KEY`, `GOOGLE_MAPS_API_KEY`

### Backend

```bash
cd backend
cp .env.example .env   # Fill in your API keys
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard will be available at `http://localhost:5173`.

### Docker

```bash
# Copy and configure environment
cp backend/.env.example backend/.env

# Start both services
docker-compose up --build
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Gemini AI API key | Yes |
| `GOOGLE_MAPS_API_KEY` | Google Maps JavaScript API key | Yes |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | Yes |
| `FIRESTORE_DATABASE` | Firestore database name | No (default) |
| `PUBSUB_TOPIC` | Pub/Sub topic for telemetry | No (default) |
| `BIGQUERY_DATASET` | BigQuery dataset name | No (default) |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe |
| `POST` | `/pubsub` | Pub/Sub push handler |
| `POST` | `/telemetry` | Direct telemetry ingestion |
| `GET` | `/gates` | All gate statuses |
| `GET` | `/gates/{id}` | Single gate detail |
| `POST` | `/gates/{id}/signage` | Update dynamic signage |
| `POST` | `/evacuation/assess` | Run EvacuNet assessment |
| `POST` | `/evacuation/trigger` | Force evacuation |
| `POST` | `/agents/dispatch` | Natural language agent command |
| `GET` | `/agents/status` | Agent system status |
| `POST` | `/reports` | Submit field report |
| `GET` | `/reports` | Retrieve recent reports |

## Stadium

**M. Chinnaswamy Stadium, Bengaluru**
- Capacity: 40,000
- Coordinates: 12.9788°N, 77.5996°E
- Gates: 8 (A through H)

## License

MIT
