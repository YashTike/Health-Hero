"use client";

import {
  ChangeEvent,
  FormEvent,
  KeyboardEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

type AgentRole = "fighter-agent" | "provider-agent";

type Message = {
  id: string;
  role: AgentRole;
  text: string;
  timestamp: string;
};

type LogEntry = {
  id: string;
  text: string;
};

type TranscriptEntry = {
  role?: string;
  message?: string;
  timestamp?: string;
};

const agentMeta: Record<
  AgentRole,
  { name: string; bubble: string; avatar: string; align: "left" | "right" }
> = {
  "fighter-agent": {
    name: "Bill Fighter",
    bubble: "bg-emerald-50 border border-emerald-100",
    avatar: "bg-emerald-100 text-emerald-800",
    align: "right",
  },
  "provider-agent": {
    name: "Provider Agent",
    bubble: "bg-white border border-sky-100",
    avatar: "bg-sky-100 text-sky-700",
    align: "left",
  },
};

const statusLabels: Record<string, string> = {
  idle: "Idle",
  upload_received: "Upload received",
  ocr_in_progress: "OCR in progress",
  ocr_complete: "Agents debating",
  ready: "Ready",
  archived: "Archived",
  pending: "Pending",
};

const getId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);

const createIdleLogEntry = (): LogEntry => ({
  id: getId(),
  text: `[${new Date().toLocaleTimeString()}] Waiting for upload…`,
});

const sanitizeBaseUrl = (value: string) => value.replace(/\/$/, "");

const API_BASE_URL = sanitizeBaseUrl(
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000"
);

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [activityLog, setActivityLog] = useState<LogEntry[]>(() => [createIdleLogEntry()]);
  const [billId, setBillId] = useState<number | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const transcriptCountRef = useRef(0);

  const appendLog = useCallback((text: string) => {
    setActivityLog((prev: LogEntry[]) => {
      const entry = {
        id: getId(),
        text: `[${new Date().toLocaleTimeString()}] ${text}`,
      };
      return [entry, ...prev].slice(0, 40);
    });
  }, []);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0] ?? null;
    setFile(nextFile);
  };

  const resetForm = () => {
    setPrompt("");
    setFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!prompt.trim() || !file) {
      return;
    }

    setMessages([]);
    setError(null);
    setIsSubmitting(true);
    setStatus("upload_received");
    appendLog("Uploading bill to backend…");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("prompt", prompt.trim());

      const response = await fetch(`${API_BASE_URL}/api/bills/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(errorData.message || errorData.detail || `HTTP error ${response.status}`);
      }

      const data = await response.json();
      const nextBillId = Number(data.billId);
      setBillId(nextBillId);
      setStatus(data.status ?? "upload_received");
      appendLog(`Bill ${nextBillId} queued for OCR + agents.`);
      resetForm();
    } catch (err) {
      console.error("Error processing bill:", err);
      setError(err instanceof Error ? err.message : "Failed to process bill. Please try again.");
      appendLog("Upload failed");
    }
    setIsSubmitting(false);
  };

  const handlePromptKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      const form = event.currentTarget.form;
      form?.requestSubmit();
    }
  };

  const fileDetails = useMemo(() => {
    if (!file) return null;
    const sizeKb = (file.size / 1024).toFixed(1);
    return `${file.name} · ${sizeKb} KB`;
  }, [file]);

  const friendlyStatus = statusLabels[status] ?? status;
  const isPolling = Boolean(billId);

  useEffect(() => {
    if (!billId) {
      transcriptCountRef.current = 0;
      return;
    }

    let cancelled = false;

    const fetchBill = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/bills/${billId}`);
        if (!response.ok) {
          const errorPayload = await response.json().catch(() => ({}));
          throw new Error(errorPayload.message || `Failed to fetch bill ${billId}`);
        }

        const payload = await response.json();
        if (cancelled) return;

        const nextStatus = payload.status ?? "pending";
        setStatus((prevStatus: string) => {
          if (prevStatus !== nextStatus) {
            appendLog(`Status updated → ${statusLabels[nextStatus] ?? nextStatus}`);
          }
          return nextStatus;
        });

        const transcript = (Array.isArray(payload.agentSession?.transcript)
          ? payload.agentSession.transcript
          : []) as TranscriptEntry[];

        if (transcript.length !== transcriptCountRef.current) {
          transcriptCountRef.current = transcript.length;
          if (transcript.length) {
            appendLog(`Received ${transcript.length} transcript message${
              transcript.length === 1 ? "" : "s"
            }.`);
          }
        }

        const normalized: Message[] = transcript
          .filter((entry: TranscriptEntry) =>
            typeof entry?.message === "string" && entry.message.trim().length
          )
          .map((entry, index) => ({
            id: `${billId}-${entry.timestamp ?? index}-${entry.role ?? "fighter-agent"}-${index}`,
            role: entry.role === "provider-agent" ? "provider-agent" : "fighter-agent",
            text: entry.message ?? "",
            timestamp: entry.timestamp ?? new Date().toISOString(),
          }));

        setMessages(normalized);
      } catch (err) {
        console.error(err);
        appendLog(err instanceof Error ? err.message : "Failed to poll bill status");
        setError(err instanceof Error ? err.message : "Unable to fetch bill details");
      }
    };

    fetchBill();
    const interval = window.setInterval(fetchBill, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [appendLog, billId]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white px-4 py-10 text-slate-900">
      <div className="mx-auto flex min-h-[80vh] max-w-6xl flex-col gap-8">
        <header className="space-y-3 text-center sm:text-left">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
            Medical Bill Fighter
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
            Upload a bill, brief the agents, and watch them negotiate
          </h1>
          <p className="text-base text-slate-600">
            The UI below talks directly to the Node API ({friendlyStatus}). Drop in a PDF or
            image, add context, and the backend will queue OCR + the debate pipeline before
            streaming the transcript back here.
          </p>
        </header>

        <main className="grid flex-1 gap-6 lg:grid-cols-[2fr_1fr]">
          <section className="flex flex-col rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_-40px_rgba(15,23,42,0.45)]">
            <div className="flex-1 space-y-6 overflow-y-auto p-6 sm:p-10">
              {error && (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                  <strong>Error:</strong> {error}
                </div>
              )}

              {messages.length === 0 ? (
                <div className="flex h-full flex-col items-center justify-center gap-4 text-center text-slate-500">
                  <div className="rounded-full border border-dashed border-slate-300 px-4 py-2 text-xs uppercase tracking-[0.2em]">
                    Awaiting transcript
                  </div>
                  <p className="max-w-md text-sm text-slate-500">
                    Submit a bill to kick off OCR + debate. Once the Python pipeline reports
                    back, the agent conversation will populate here automatically.
                  </p>
                </div>
              ) : (
                <div className="space-y-6">
                  {messages.map((message) => (
                    <MessageBubble key={message.id} message={message} />
                  ))}
                </div>
              )}
            </div>

            <form
              className="space-y-4 border-t border-slate-100 bg-slate-50/70 px-4 py-6 sm:px-8"
              onSubmit={handleSubmit}
            >
              <textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                onKeyDown={handlePromptKeyDown}
                placeholder="Describe what needs to be negotiated or questioned…"
                className="min-h-[140px] w-full resize-none rounded-2xl border border-slate-200 bg-white px-4 py-3 text-base text-slate-900 outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200"
              />
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <label className="flex w-full cursor-pointer flex-col rounded-2xl border border-dashed border-slate-300 bg-white px-4 py-3 text-sm text-slate-500 transition hover:border-slate-400 hover:text-slate-700 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex flex-col">
                    <span className="font-medium text-slate-700">
                      Attach photo or PDF
                    </span>
                    <span>
                      {fileDetails || "Agents need a supporting document to start"}
                    </span>
                  </div>
                  <span className="mt-2 inline-flex items-center justify-center rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold text-white sm:mt-0">
                    Browse
                  </span>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,application/pdf"
                    onChange={handleFileChange}
                    className="sr-only"
                  />
                </label>
                <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
                  <button
                    type="submit"
                    disabled={!prompt.trim() || !file || isSubmitting}
                    className="w-full rounded-2xl bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                  >
                    {isSubmitting ? "Uploading…" : billId ? "Re-run agents" : "Send to agents"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setBillId(null);
                      setStatus("idle");
                      setMessages([]);
                      setError(null);
                      resetForm();
                      setActivityLog([createIdleLogEntry()]);
                      appendLog("Reset panel");
                    }}
                    className="w-full rounded-2xl border border-slate-200 px-6 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-300"
                  >
                    Reset
                  </button>
                </div>
              </div>
            </form>
          </section>

          <aside className="flex flex-col gap-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.45)]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
                Status
              </p>
              <p className="mt-2 text-3xl font-semibold text-slate-900">{friendlyStatus}</p>
              <p className="text-sm text-slate-500">
                {isPolling
                  ? "Polling backend every 5s for OCR + transcript updates."
                  : "Submit a bill to start the pipeline."}
              </p>
            </div>

            <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
                Bill ID
              </p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">
                {billId ?? "—"}
              </p>
            </div>

            <div className="flex-1 space-y-3">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
                Activity log
              </p>
              <div className="max-h-[360px] overflow-y-auto rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                {activityLog.length === 0 ? (
                  <p>Waiting for events…</p>
                ) : (
                  <ul className="space-y-2">
                    {activityLog.map((entry) => (
                      <li key={entry.id} className="leading-snug">
                        {entry.text}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </aside>
        </main>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const meta = agentMeta[message.role];
  const avatarInitials = meta.name
    .split(" ")
    .map((part) => part.at(0))
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const isProvider = message.role === "provider-agent";

  return (
    <div
      className={`flex gap-3 ${
        isProvider ? "justify-start" : "justify-end text-right"
      }`}
    >
      {isProvider && (
        <span
          className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold ${meta.avatar}`}
        >
          {avatarInitials}
        </span>
      )}
      <div
        className={`max-w-lg rounded-3xl px-4 py-3 text-sm text-slate-700 shadow-sm ${meta.bubble}`}
      >
        <div className="mb-1 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
          {meta.name}
        </div>
        <p className="leading-relaxed text-slate-900">{message.text}</p>
        <div className="mt-3 text-[11px] uppercase tracking-[0.2em] text-slate-400">
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
      {!isProvider && (
        <span
          className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold ${meta.avatar}`}
        >
          {avatarInitials}
        </span>
      )}
    </div>
  );
}
