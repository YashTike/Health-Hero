import express, { type ErrorRequestHandler } from 'express';
import cors from 'cors';
import morgan from 'morgan';
import path from 'path';
import billsRouter from './routes/bills';

export const createApp = () => {
  const app = express();

  app.use(cors());
  app.use(express.json({ limit: '2mb' }));
  app.use(morgan('dev'));

  const staticDir = path.resolve(process.cwd(), 'public');
  app.get('/', (_req, res) => {
    res.json({
      message: 'Frontend moved to the Next.js app. Run `cd frontend && NEXT_PUBLIC_API_URL=http://localhost:4000 npm run dev` and open http://localhost:3000.',
    });
  });
  app.use(express.static(staticDir));

  app.get('/health', (_req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
  });

  app.use('/api/bills', billsRouter);

  const errorHandler: ErrorRequestHandler = (err, _req, res, _next) => {
    const status = err instanceof SyntaxError ? 400 : 500;
    // eslint-disable-next-line no-console
    console.error(err);
    res.status(status).json({
      message: err instanceof Error ? err.message : 'Unexpected error',
    });
  };

  app.use(errorHandler);

  return app;
};
