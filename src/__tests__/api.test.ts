import fs from 'fs';
import path from 'path';
import request from 'supertest';
import type BetterSqlite3 from 'better-sqlite3';

jest.mock('../services/orchestrationService', () => ({
  enqueueOcrJob: jest.fn().mockResolvedValue(undefined),
  notifyMedicalAgent: jest.fn().mockResolvedValue(undefined),
}));

import { enqueueOcrJob, notifyMedicalAgent } from '../services/orchestrationService';

const fixturePath = path.resolve(__dirname, '../../tests/fixtures/sample-bill.txt');
const uploadDir = path.resolve(__dirname, '../../tmp/test-uploads');

let app: ReturnType<typeof import('../app')['createApp']>;
let db: BetterSqlite3.Database;

describe('Medical Bill Fighter API', () => {
  beforeAll(async () => {
    process.env.NODE_ENV = 'test';
    process.env.SQLITE_PATH = ':memory:';
    process.env.UPLOAD_DIR = uploadDir;
    fs.rmSync(uploadDir, { recursive: true, force: true });

    const [{ createApp }, { db: database }] = await Promise.all([
      import('../app'),
      import('../db/connection'),
    ]);

    app = createApp();
    db = database;
  });

  beforeEach(() => {
    jest.clearAllMocks();
    resetDatabase();
  });

  const resetDatabase = () => {
    const tables = ['agent_sessions', 'scripts', 'analyses', 'line_items', 'bills'];
    tables.forEach((table) => {
      db.prepare(`DELETE FROM ${table}`).run();
    });
  };

  it('handles upload -> OCR -> agent orchestration flow', async () => {
    const uploadResponse = await request(app)
      .post('/api/bills/upload')
      .field('prompt', 'spot every duplicate and overpriced line item')
      .field('patientName', 'Test Patient')
      .field('providerName', 'Test Provider')
      .attach('file', fixturePath);

    expect(uploadResponse.status).toBe(202);
    expect(uploadResponse.body).toHaveProperty('billId');
    const billId = uploadResponse.body.billId as number;
    expect(enqueueOcrJob).toHaveBeenCalledWith(
      expect.objectContaining({
        billId,
        prompt: 'spot every duplicate and overpriced line item',
        filePath: expect.stringContaining('uploads'),
      })
    );

    const ocrPayload = {
      patientName: 'OCR Patient',
      providerName: 'OCR Provider',
      originalFilename: 'ocr-bill.pdf',
      notes: 'Parsed via OCR',
      ocrText: 'Full OCR output',
      lineItems: [
        { description: 'Office visit', code: '99213', amount: 250, quantity: 1 },
        { description: 'Lab panel', code: '80050', amount: 600, quantity: 1 },
      ],
    };

    const ocrResponse = await request(app)
      .post(`/api/bills/${billId}/ocr-callback`)
      .send(ocrPayload);

    expect(ocrResponse.status).toBe(200);
    expect(ocrResponse.body.status).toBe('ocr_complete');
    expect(ocrResponse.body.lineItems).toHaveLength(2);
    expect(notifyMedicalAgent).toHaveBeenCalledWith(
      expect.objectContaining({
        billId,
        prompt: 'spot every duplicate and overpriced line item',
        ocrText: 'Full OCR output',
        lineItems: expect.any(Array),
      })
    );

    const transcript = [
      {
        role: 'fighter-agent' as const,
        message: 'We need a discount.',
        timestamp: new Date().toISOString(),
      },
      {
        role: 'provider-agent' as const,
        message: 'We can lower it by 20%.',
        timestamp: new Date().toISOString(),
      },
    ];

    const agentSessionResponse = await request(app)
      .post(`/api/bills/${billId}/agent-session`)
      .send({ transcript });

    expect(agentSessionResponse.status).toBe(200);
    expect(agentSessionResponse.body.transcript).toHaveLength(2);

    const agentSessionFetch = await request(app).get(`/api/bills/${billId}/agent-session`);
    expect(agentSessionFetch.status).toBe(200);
    expect(agentSessionFetch.body.transcript).toHaveLength(2);
  });

  it('creates a bill directly when structured data is provided', async () => {
    const createResponse = await request(app)
      .post('/api/bills')
      .send({
        patientName: 'Structured Patient',
        providerName: 'Structured Provider',
        notes: 'Direct payload',
        lineItems: [
          { description: 'EKG', code: '93000', amount: 95, quantity: 1 },
        ],
      });

    expect(createResponse.status).toBe(201);
    expect(createResponse.body.status).toBe('ready');
    expect(createResponse.body.lineItems).toHaveLength(1);
    expect(createResponse.body.lineItems[0]).toHaveProperty('flags');
  });
});
