export type BillStatus =
  | 'upload_received'
  | 'ocr_in_progress'
  | 'ocr_complete'
  | 'ready'
  | 'archived'
  | 'pending';

export interface LineItemInput {
  description: string;
  code?: string;
  quantity?: number;
  amount: number;
}

export interface BillInput {
  patientName?: string;
  providerName?: string;
  originalFilename?: string;
  notes?: string;
  lineItems: LineItemInput[];
}

export interface BillUploadPayload {
  prompt: string;
  patientName?: string;
  providerName?: string;
  notes?: string;
  storedFilePath: string;
  originalFilename?: string;
}

export interface OcrExtractionPayload extends BillInput {
  ocrText?: string;
}

export interface AgentSessionPayload {
  transcript: Array<{
    role: 'fighter-agent' | 'provider-agent';
    message: string;
    timestamp: string;
  }>;
}

export interface MedicalAgentDispatchPayload {
  billId: number;
  prompt?: string;
  ocrText?: string;
  lineItems: Array<LineItemInput & { flags?: unknown }>;
}
