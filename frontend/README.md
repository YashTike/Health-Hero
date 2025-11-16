## Medical Bill Fighter Frontend

Next.js 16 + React 19 interface for the Medical Bill Fighter stack. It uploads bills, relays prompts to the Node API, and polls for OCR + agent debate updates in real time.

### Prerequisites

- Node.js 20+
- Backend API running locally (default: `http://localhost:4000`)

### Environment

Set `NEXT_PUBLIC_API_URL` so the browser knows where to send requests. Create `.env.local` in this folder:

```
NEXT_PUBLIC_API_URL=http://localhost:4000
```

If omitted, the app falls back to that localhost URL automatically.

### Install & Run

```bash
npm install
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000). The form will:

1. `POST /api/bills/upload` with the file + prompt.
2. Poll `GET /api/bills/:billId` every 5 seconds to surface the bill status and agent transcript.

### Production build

```bash
npm run build
npm start
```

Deploy the Next.js output anywhere (Vercel, Docker, etc.). Configure `NEXT_PUBLIC_API_URL` to point at the deployed backend origin.
