import { z } from 'zod';
import { db } from '../db/connection';
import type {
  AgentSessionPayload,
  BillInput,
  BillUploadPayload,
  OcrExtractionPayload,
} from '../types/bill';
import { evaluateLineItemAgainstBenchmark, findBenchmarkByCode } from './costBenchmarkService';

interface BillRow {
  id: number;
  patient_name?: string;
  provider_name?: string;
  status: string;
  uploaded_at: string;
  original_filename?: string;
  notes?: string;
  prompt?: string;
  file_path?: string;
  ocr_text?: string;
}

interface LineItemRow {
  id: number;
  bill_id: number;
  description: string;
  code?: string;
  quantity: number;
  amount: number;
  flags?: string;
}

interface AgentSessionRow {
  id: number;
  bill_id: number;
  transcript_json?: string;
  created_at: string;
}

interface LineItemWithFlags extends Omit<LineItemRow, 'flags'> {
  flags?: unknown;
}

export interface BillDetail extends BillRow {
  lineItems: LineItemWithFlags[];
  agentSession: (AgentSessionRow & { transcript: unknown[] }) | null;
}

const lineItemSchema = z.object({
  description: z.string(),
  code: z.string().optional(),
  quantity: z.number().int().positive().optional().default(1),
  amount: z.number().nonnegative(),
});

const billSchema = z.object({
  patientName: z.string().optional(),
  providerName: z.string().optional(),
  originalFilename: z.string().optional(),
  notes: z.string().optional(),
  lineItems: z.array(lineItemSchema).min(1),
});

const billShellSchema = z.object({
  prompt: z.string().min(1),
  patientName: z.string().optional(),
  providerName: z.string().optional(),
  originalFilename: z.string().optional(),
  notes: z.string().optional(),
  storedFilePath: z.string().min(1),
});

const ocrCallbackSchema = z.object({
  patientName: z.string().optional(),
  providerName: z.string().optional(),
  originalFilename: z.string().optional(),
  notes: z.string().optional(),
  lineItems: z.array(lineItemSchema).min(1),
  ocrText: z.string().optional(),
});

const agentSessionSchema = z.object({
  transcript: z.array(
    z.object({
      role: z.enum(['fighter-agent', 'provider-agent']),
      message: z.string(),
      timestamp: z.string(),
    })
  ),
});

const insertLineItems = (billId: number, lineItems: z.infer<typeof lineItemSchema>[]) => {
  const insertLineItem = db.prepare(
    `INSERT INTO line_items (bill_id, description, code, quantity, amount, flags)
     VALUES (@billId, @description, @code, @quantity, @amount, @flags)`
  );

  lineItems.forEach((item) => {
    const benchmark = findBenchmarkByCode(item.code);
    const evaluation = evaluateLineItemAgainstBenchmark(item.amount, benchmark);
    const flags = {
      ...(evaluation.benchmark ? { benchmark: evaluation.benchmark } : {}),
      variance: evaluation.variance,
      isOverpriced: evaluation.isOverpriced,
    };

    insertLineItem.run({
      billId,
      ...item,
      quantity: item.quantity ?? 1,
      flags: JSON.stringify(flags),
    });
  });
};

const clearLineItemsForBill = (billId: number) => {
  db.prepare('DELETE FROM line_items WHERE bill_id = ?').run(billId);
};

export const createBill = (payload: BillInput) => {
  const data = billSchema.parse(payload);
  const insertBill = db.prepare(
    `INSERT INTO bills (patient_name, provider_name, original_filename, notes, status)
     VALUES (@patientName, @providerName, @originalFilename, @notes, @status)`
  );
  const result = insertBill.run({
    patientName: data.patientName ?? null,
    providerName: data.providerName ?? null,
    originalFilename: data.originalFilename ?? null,
    notes: data.notes ?? null,
    status: 'ready',
  });
  const billId = Number(result.lastInsertRowid);
  insertLineItems(billId, data.lineItems);
  return getBillById(billId);
};

export const createBillShell = (payload: BillUploadPayload) => {
  const data = billShellSchema.parse(payload);
  const insertBill = db.prepare(
    `INSERT INTO bills (patient_name, provider_name, original_filename, notes, prompt, file_path, status)
     VALUES (@patientName, @providerName, @originalFilename, @notes, @prompt, @storedFilePath, @status)`
  );
  const result = insertBill.run({
    patientName: data.patientName ?? null,
    providerName: data.providerName ?? null,
    originalFilename: data.originalFilename ?? null,
    notes: data.notes ?? null,
    prompt: data.prompt,
    storedFilePath: data.storedFilePath,
    status: 'upload_received',
  });
  const billId = Number(result.lastInsertRowid);
  return getBillById(billId);
};

export const attachOcrResults = (billId: number, payload: OcrExtractionPayload) => {
  const data = ocrCallbackSchema.parse(payload);
  const billExists = db.prepare('SELECT id FROM bills WHERE id = ?').get(billId) as
    | { id: number }
    | undefined;

  if (!billExists) {
    throw new Error('Bill not found');
  }

  db.prepare(
    `UPDATE bills
     SET patient_name = @patientName,
         provider_name = @providerName,
         original_filename = COALESCE(@originalFilename, original_filename),
         notes = COALESCE(@notes, notes),
         ocr_text = @ocrText,
         status = @status
     WHERE id = @billId`
  ).run({
    billId,
    patientName: data.patientName ?? null,
    providerName: data.providerName ?? null,
    originalFilename: data.originalFilename ?? null,
    notes: data.notes ?? null,
    ocrText: data.ocrText ?? null,
    status: 'ocr_complete',
  });

  clearLineItemsForBill(billId);
  insertLineItems(billId, data.lineItems);
  return getBillById(billId);
};

export const getBillById = (billId: number): BillDetail | null => {
  const bill = db.prepare('SELECT * FROM bills WHERE id = ?').get(billId) as BillRow | undefined;
  if (!bill) return null;

  const lineItemRows = db.prepare('SELECT * FROM line_items WHERE bill_id = ?').all(billId) as LineItemRow[];

  const lineItems: LineItemWithFlags[] = lineItemRows.map((row) => ({
    ...row,
    flags: row.flags ? JSON.parse(row.flags) : undefined,
  }));

  const agentSession = db
    .prepare('SELECT * FROM agent_sessions WHERE bill_id = ? ORDER BY created_at DESC LIMIT 1')
    .get(billId) as AgentSessionRow | undefined;

  return {
    ...bill,
    lineItems,
    agentSession: agentSession
      ? {
          ...agentSession,
          transcript: agentSession.transcript_json
            ? JSON.parse(agentSession.transcript_json)
            : [],
        }
      : null,
  };
};

export const saveAgentSession = (billId: number, payload: AgentSessionPayload) => {
  const data = agentSessionSchema.parse(payload);
  db.prepare(
    `INSERT INTO agent_sessions (bill_id, transcript_json)
     VALUES (@billId, @transcript)`
  ).run({
    billId,
    transcript: JSON.stringify(data.transcript),
  });

  return getBillById(billId);
};
