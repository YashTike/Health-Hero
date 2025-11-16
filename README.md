# Medical Bill Fighter

Full-stack reference implementation that ingests raw medical bills, enriches them with OCR + LLM analysis, and surfaces the results through a modern Next.js UI. The repo intentionally co-locates all three major pieces so they can share configuration, fixtures, and deployment tooling.

## Stack Overview
- **Node.js + Express API (`src/`)** – Handles uploads, persists state in SQLite (via Better-SQLite3), and orchestrates the Python pipeline.
- **Python OCR + Agent pipeline (`backend/`)** – Uses pdfplumber/pytesseract for extraction, OpenAI agents for analysis + negotiation content, and an optional debate simulation for transcripts.
- **Next.js 16 frontend (`frontend/`)** – React 19 app that uploads files, polls the API for bill state, and renders transcripts + insights.

## System Architecture
### 1. TypeScript API layer
- `src/app.ts` wires CORS, logging, JSON parsing, and plugs in the `bills` router under `/api/bills` plus `/health` for readiness checks.
- `src/routes/bills.ts` exposes:
  - `POST /api/bills/upload` (multipart) – creates a shell bill, saves the file to `UPLOAD_DIR`, and enqueues the OCR/LLM pipeline.
  - `POST /api/bills` – bypasses OCR when structured line items are already available.
  - `GET /api/bills/:billId` – returns the aggregated bill, line items, analysis, transcripts, and status.
  - `POST /api/bills/:billId/ocr-callback` – allows the Python side (or tests) to push structured data back in.
  - `GET/POST /api/bills/:billId/agent-session` – persists the debate transcript once generated.
- `src/services/orchestrationService.ts` spawns the Python runner via `child_process.spawn`, passing `PYTHON_BIN`, script path, timeout, and debate knobs defined in `src/config/env.ts`.
- `src/db/connection.ts` bootstraps Better-SQLite3, applying auto migrations defined in `src/db/schema.ts` (tables for bills, line_items, analyses, scripts, agent_sessions).

### 2. Python OCR + LLM pipeline
- Entry point: `backend/run_pipeline_cli.py`, invoked with `--file`, `--prompt`, `--model`, and debate controls.
- OCR: `backend/ocr/pipeline.py` tries `TextPDFExtractor` (pdfplumber) first, falls back to `ImageOCRExtractor` (pytesseract + pdf2image + poppler) so both digital and scanned PDFs are supported.
- LLM agents: `backend/agents/pipeline.py` chains extraction → analysis → negotiation, powered by the `openai` SDK. Prompts live in `backend/agents/*.py`.
- Debate system: `backend/agents/debate.py` and `DebateManager` stage multi-round exchanges between a “fighter” and “hospital” persona; results are summarized via `generate_debate_summary`.

### 3. Next.js frontend
- Located in `frontend/`, built with Next.js 16 / React 19 / TypeScript.
- `src/app/page.tsx` renders the upload form, progress polling, and transcript viewer. It relies on `NEXT_PUBLIC_API_URL` (default `http://localhost:4000`).
- Uses the shared `public/` assets for branding and Tailwind v4/PostCSS for styling.

## Processing Lifecycle
1. **Upload** – User submits prompt + bill via the frontend or direct `POST /api/bills/upload`. Multer stores the raw file in `UPLOAD_DIR`; a shell bill is inserted with status `pending`.
2. **Pipeline orchestration** – `enqueueOcrJob` fires `run_pipeline_cli.py` with the stored path. Output is streamed over stdout as JSON.
3. **OCR + Extraction** – Python extracts readable text (pdfplumber) or rasterizes pages for Tesseract when needed, then emits normalized line items.
4. **LLM Analysis** – Agents annotate each line item with expected pricing, issues, and narrative negotiation assets. Optional debate transcripts are generated for richer UX.
5. **Persistence** – The Node service writes line items + OCR text via `attachOcrResults`, logs analysis aggregates, and stores the transcript in `agent_sessions`.
6. **Frontend polling** – UI hits `GET /api/bills/:billId` every few seconds to reflect status transitions and conversation updates.

## Data Model Snapshot
| Table | Purpose |
| --- | --- |
| `bills` | Core metadata (patient/provider, prompt, original filename, status, OCR text, file path). |
| `line_items` | Normalized description/code/quantity/amount per bill. |
| `analyses` | Stores aggregated cost comparisons and summary JSON. |
| `scripts` | Negotiation email + phone script artifacts. |
| `agent_sessions` | JSON transcript of the debate or medical agent dialogue. |

## Configuration & Environment
Create a root `.env` (see `.env.example`) and extend it with:

| Variable | Description |
| --- | --- |
| `PORT` | Express listen port (default `4000`). |
| `SQLITE_PATH` | SQLite filename or `:memory:` for ephemeral runs. |
| `UPLOAD_DIR` | Directory for Multer uploads. Created automatically if missing. |
| `PYTHON_BIN` | Absolute path to the Python interpreter (recommend the repo’s `.venv/bin/python`). |
| `PYTHON_AGENT_SCRIPT` | Defaults to `backend/run_pipeline_cli.py`; change if you wrap the pipeline. |
| `PYTHON_AGENT_TIMEOUT_MS` | Kill-switch for long OCR/LLM runs. |
| `PYTHON_DEBATE_ROUNDS` / `PYTHON_DEBATE_DISABLED` | Control debate simulation volume. |
| `OPENAI_API_KEY` | Required by the Python agents; load via `.env` or shell export so both Node and Python inherit it. |

Frontend-specific config lives in `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:4000
```

## Getting Started
### 1. Backend + Python pipeline
```bash
# Install Node dependencies
npm install  # or yarn install

# Create/refresh the Python virtual environment
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```
Install native OCR binaries once per machine:
```bash
brew install tesseract
brew install poppler
```
Verify tooling:
```bash
source .venv/bin/activate
which python
python - <<'PY'
import pdfplumber, pytesseract, openai
print("OCR stack ready")
PY
```

### 2. Frontend
```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:4000 npm run dev
```
The app serves at http://localhost:3000.

### 3. Running everything together
```bash
# Terminal 1 – backend API
npm run dev  # or yarn dev

# Terminal 2 – Next.js UI
cd frontend
npm run dev
```
Hit `POST /api/bills/upload` via the UI, then monitor the backend logs for Python pipeline output. Health check: `curl http://localhost:4000/health`.

## Useful Scripts
| Command | Description |
| --- | --- |
| `npm run dev` | Starts the Express API with `ts-node-dev` (hot reload). |
| `npm run build && npm start` | Type-checks, emits `dist/`, and serves the compiled API. |
| `npm test` | Runs the Jest suite in `src/__tests__/`. |
| `python backend/run_pipeline_cli.py --file bill.pdf --prompt "Focus on imaging"` | Standalone pipeline smoke-test without the Node API. |
| `cd frontend && npm run build && npm start` | Production-grade Next.js build. |

## Troubleshooting
- **`ModuleNotFoundError: pdfplumber`** – Activate the correct `.venv` (`source .venv/bin/activate`) and re-run `pip install -r backend/requirements.txt`. Ensure `PYTHON_BIN` points to that interpreter.
- **`TesseractNotFoundError` or empty OCR output** – Install `tesseract` + `poppler`, confirm `tesseract --version` works, and provide high-resolution PDFs.
- **Pipeline timeouts** – Increase `PYTHON_AGENT_TIMEOUT_MS`, or temporarily disable the debate simulation by setting `PYTHON_DEBATE_DISABLED=true`.
- **Uploads stuck in `pending`** – Check `uploads/` permissions and backend logs; `run_pipeline_cli.py` writes errors to stderr which surface through the Node process.

## Contributing / Next Steps
- Expand automated tests (service-level, integration between Node and Python).
- Add WebSocket or SSE updates instead of polling for near-real-time transcripts.
- Integrate real cost benchmark data or external pricing APIs in `services/costBenchmarkService.ts`.
- Containerize the stack (Dockerfile + docker-compose) for parity between contributors and CI.
