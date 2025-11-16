import { spawn } from 'node:child_process';

import { env } from '../config/env';
import { attachOcrResults, saveAgentSession } from './billService';
import type { AgentSessionPayload, LineItemInput, MedicalAgentDispatchPayload } from '../types/bill';

export interface OcrJobPayload {
  billId: number;
  filePath: string;
  prompt: string;
}

interface PipelineLineItem {
  code?: string;
  description?: string;
  quantity?: number;
  price?: number;
  notes?: string | null;
}

interface DebateMessage {
  role?: string;
  content?: string;
}

interface PythonPipelineResult {
  ocr_text?: string;
  extraction?: PipelineLineItem[];
  debate_transcript?: DebateMessage[];
}

const runPythonPipeline = ({
  filePath,
  prompt,
}: {
  filePath: string;
  prompt: string;
}): Promise<PythonPipelineResult> => {
  return new Promise((resolve, reject) => {
    const scriptPath = env.pythonAgentScript;
    const args = ['--file', filePath];
    if (prompt) {
      args.push('--prompt', prompt);
    }
    args.push('--model', 'gpt-4o');
    args.push('--max-debate-rounds', String(env.pythonDebateRounds));
    if (env.pythonDebateDisabled) {
      args.push('--no-debate');
    }

    const child = spawn(env.pythonBin, [scriptPath, ...args], {
      cwd: process.cwd(),
    });

    const stdoutChunks: Buffer[] = [];
    const stderrChunks: Buffer[] = [];

    const killTimer = setTimeout(() => {
      child.kill('SIGKILL');
      reject(new Error('Python pipeline timed out'));
    }, env.pythonAgentTimeoutMs);

    child.stdout.on('data', (chunk) => stdoutChunks.push(Buffer.from(chunk)));
    child.stderr.on('data', (chunk) => stderrChunks.push(Buffer.from(chunk)));

    child.on('error', (error) => {
      clearTimeout(killTimer);
      reject(error);
    });

    child.on('close', (code) => {
      clearTimeout(killTimer);
      const stdout = Buffer.concat(stdoutChunks).toString();
      const stderr = Buffer.concat(stderrChunks).toString();

      if (code !== 0) {
        reject(new Error(`Python pipeline exited with code ${code}: ${stderr || stdout}`));
        return;
      }

      try {
        const parsed = JSON.parse(stdout);
        resolve(parsed);
      } catch (error) {
        reject(new Error(`Failed to parse Python output: ${(error as Error).message}`));
      }
    });
  });
};

const convertLineItems = (items: PipelineLineItem[]): LineItemInput[] => {
  const normalized: LineItemInput[] = [];

  items.forEach((item) => {
    if (!item.description) return;
    const amount = Number(item.price ?? 0);
    const quantity = Number.isFinite(item.quantity) ? Number(item.quantity) : 1;

    const normalizedItem: LineItemInput = {
      description: item.description,
      amount: amount >= 0 ? amount : 0,
      quantity: quantity > 0 ? quantity : 1,
    };

    if (item.code) {
      normalizedItem.code = item.code;
    }

    normalized.push(normalizedItem);
  });

  return normalized;
};

const persistAgentTranscript = async (billId: number, debateTranscript: DebateMessage[] = []) => {
  if (!debateTranscript.length) return;

  const transcript: AgentSessionPayload['transcript'] = debateTranscript.map((message, index) => {
    const role = message.role === 'hospital' ? 'provider-agent' : 'fighter-agent';
    return {
      role,
      message: message.content ?? '',
      timestamp: new Date(Date.now() + index * 1000).toISOString(),
    };
  });

  if (transcript.every((entry) => !entry.message.trim())) {
    return;
  }

  await saveAgentSession(billId, { transcript });
};

const processOcrJob = async ({ billId, filePath, prompt }: OcrJobPayload) => {
  const pipelineResult = await runPythonPipeline({ filePath, prompt });
  const lineItems = convertLineItems(pipelineResult.extraction ?? []);

  if (!lineItems.length) {
    throw new Error('Python pipeline returned no extractable line items');
  }

  await attachOcrResults(billId, {
    lineItems,
    ocrText: pipelineResult.ocr_text ?? '',
  });

  await persistAgentTranscript(billId, pipelineResult.debate_transcript);
};

export const enqueueOcrJob = async ({ billId, filePath, prompt }: OcrJobPayload) => {
  processOcrJob({ billId, filePath, prompt }).catch((error) => {
    console.error('[OCR] Pipeline failed', {
      billId,
      error: error instanceof Error ? error.message : error,
    });
  });
};

export const notifyMedicalAgent = async (payload: MedicalAgentDispatchPayload) => {
  console.info('[Agent] Payload acknowledged (pipeline handled upstream)', {
    billId: payload.billId,
    lineItemCount: payload.lineItems.length,
  });
};
