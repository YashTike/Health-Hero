import { Router } from 'express';
import multer from 'multer';
import { z } from 'zod';
import { env } from '../config/env';
import {
  createBill,
  createBillShell,
  attachOcrResults,
  getBillById,
  saveAgentSession,
} from '../services/billService';
import { enqueueOcrJob, notifyMedicalAgent } from '../services/orchestrationService';

const router = Router();
const upload = multer({ dest: env.uploadDir });

const billIdParamSchema = z.object({
  billId: z.coerce.number().int().positive(),
});

router.post('/', (req, res, next) => {
  try {
    const bill = createBill(req.body);
    res.status(201).json(bill);
  } catch (error) {
    next(error);
  }
});

router.post('/upload', upload.single('file'), async (req, res, next) => {
  try {
    if (!req.file) {
      res.status(400).json({ message: 'A file upload is required.' });
      return;
    }

    const bill = createBillShell({
      prompt: req.body.prompt,
      patientName: req.body.patientName,
      providerName: req.body.providerName,
      notes: req.body.notes,
      storedFilePath: req.file.path,
      originalFilename: req.file.originalname,
    });

    if (!bill) {
      throw new Error('Bill shell could not be created');
    }

    await enqueueOcrJob({
      billId: bill.id,
      filePath: req.file.path,
      prompt: bill.prompt ?? req.body.prompt ?? '',
    });

    res.status(202).json({ billId: bill.id, status: bill.status, message: 'OCR job queued' });
  } catch (error) {
    next(error);
  }
});

router.get('/:billId', (req, res, next) => {
  try {
    const { billId } = billIdParamSchema.parse(req.params);
    const bill = getBillById(billId);
    if (!bill) {
      res.status(404).json({ message: 'Bill not found' });
      return;
    }
    res.json(bill);
  } catch (error) {
    next(error);
  }
});

router.post('/:billId/ocr-callback', async (req, res, next) => {
  try {
    const { billId } = billIdParamSchema.parse(req.params);
    const updated = attachOcrResults(billId, req.body);
    if (updated) {
      await notifyMedicalAgent({
        billId,
        ...(updated.prompt ? { prompt: updated.prompt } : {}),
        ...(updated.ocr_text ? { ocrText: updated.ocr_text } : {}),
        lineItems: updated.lineItems,
      });
    }
    res.json(updated);
  } catch (error) {
    next(error);
  }
});

router
  .route('/:billId/agent-session')
  .post((req, res, next) => {
    try {
      const { billId } = billIdParamSchema.parse(req.params);
      const updated = saveAgentSession(billId, req.body);
      res.json(updated?.agentSession);
    } catch (error) {
      next(error);
    }
  })
  .get((req, res, next) => {
    try {
      const { billId } = billIdParamSchema.parse(req.params);
      const bill = getBillById(billId);
      if (!bill) {
        res.status(404).json({ message: 'Bill not found' });
        return;
      }
      res.json(bill.agentSession);
    } catch (error) {
      next(error);
    }
  });

export default router;
