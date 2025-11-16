# Medical Bill Fighter Backend

Node.js + Express API for hackathon prototype that ingests raw medical bill uploads (file + prompt), runs them through OCR + AI agents, enriches line items with mock cost benchmarks, and surfaces negotiation artifacts back to the frontend.

## Features

- In-memory (or file-backed) SQLite database managed through Better SQLite3
- Upload pipeline that stores the file, queues OCR, and routes OCR callbacks into the structured bill store
- REST endpoints for creating bills, handling OCR callbacks, and persisting simulated fighter/provider chat transcripts
- Background OCR + agent pipeline driven by the Python CLI (Tesseract + OpenAI)
- Mock CPT/HCPCS benchmark catalog with helper utilities to flag overpriced line items
- Health-check endpoint and centralized error handling
- TypeScript-first tooling with `ts-node-dev` for rapid iteration

## Project Structure

```
src/
  config/        // environment loader
  db/            // sqlite connection + schema
  routes/        // Express routers
  services/      // business logic + cost benchmarks
  mocks/         // hackathon benchmark dataset
```

## Getting Started

### 1. Install dependencies

```bash
npm install
```

### 2. Install Python toolchain

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Also install the native OCR dependencies (covered in `backend/README.md`):

- Tesseract OCR
- Poppler utilities

### 3. Configure environment

Copy `.env.example` to `.env` and tweak as needed. Use `SQLITE_PATH=:memory:` for volatile runs or provide a filename to persist across restarts. `UPLOAD_DIR` controls where Multer stores incoming files before they are handed to OCR.

#### Python integration environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `PYTHON_BIN` | `python3` | Interpreter used to spawn the CLI. |
| `PYTHON_AGENT_SCRIPT` | `backend/run_pipeline_cli.py` | Path to the OCR + agent runner. |
| `PYTHON_AGENT_TIMEOUT_MS` | `120000` | Timeout before the Node process kills the Python job. |
| `PYTHON_DEBATE_ROUNDS` | `3` | Number of fighter vs. hospital debate rounds to generate. |
| `PYTHON_DEBATE_DISABLED` | `false` | Set to `true` to skip debate/transcript generation. |

### 4. Run the API in development

```bash
npm run dev
```

The Express API listens on [http://localhost:4000](http://localhost:4000) by default. Use this origin as the `NEXT_PUBLIC_API_URL` for the frontend (see below).

### 5. Run the Next.js frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:4000 npm run dev
```

The UI runs on [http://localhost:3000](http://localhost:3000) and proxies all uploads + polling back to the API server.

### 6. Build for production

```bash
npm run build
npm start
```

### 7. Run the API test suite

```bash
npm test
```

## API Overview

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/bills/upload` | Multipart upload (fields: `file`, `prompt`, optional patient/provider metadata). Stores shell bill, queues OCR job, returns `{ billId, status }`. |
| `POST` | `/api/bills/:billId/ocr-callback` | Called by OCR service with structured line items + optional raw text; persists data and immediately dispatches to the medical agent. |
| `POST` | `/api/bills` | Directly create a bill when structured line items are already available (bypasses OCR). |
| `GET` | `/api/bills/:billId` | Fetch full bill snapshot, including latest fighter/provider transcript. |
| `POST/GET` | `/api/bills/:billId/agent-session` | Save or fetch the latest fighter/provider chat transcript. |
| `GET` | `/health` | Basic heartbeat for ops checks. |

All non-upload endpoints accept/return JSON. Validation is handled via `zod`, and mock benchmark utilities automatically annotate line items with variance information.

## End-to-End Flow

1. **Upload** – Frontend sends prompt + file to `POST /api/bills/upload`. Backend stores metadata, marks status `upload_received`, and fires off the Python CLI runner in the background.
2. **Python pipeline** – `backend/run_pipeline_cli.py` performs OCR, extraction, analysis, negotiation, and the debate simulation. Once results are ready, the Node backend ingests the structured line items via its existing callback logic and persists the generated fighter/provider transcript.
3. **Frontend consumption** – UI polls `GET /api/bills/:billId` (or eventually subscribes via websockets) to show status transitions, annotated line items, and the simulated provider conversation.

## Next.js Frontend

The dedicated UI lives in `frontend/` and is built with Next.js 16 + React 19. It speaks to this backend by:

1. Sending uploads to `POST /api/bills/upload` with the prompt + file.
2. Polling `GET /api/bills/:billId` every few seconds to reflect OCR progress and stream the agent debate transcript.
3. Surfacing the activity log, bill status, and full conversation in a modern interface.

Set `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:4000`) so the browser knows where to send requests. When deploying, host the backend + Next.js app separately or behind the same origin—only the environment variable needs to change.

## Next Steps

- Add automated tests (service-level + route smoke tests)
- Extend mock benchmarks or connect to live pricing APIs
- Wire WebSocket/SSE channel for real-time agent exchanges
- Add request logging persistence and metrics for production readiness
