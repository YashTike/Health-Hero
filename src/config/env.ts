import { config } from 'dotenv';
import fs from 'fs';
import path from 'path';

const envFile = process.env.NODE_ENV === 'test' ? '.env.test' : '.env';
config({ path: path.resolve(process.cwd(), envFile) });

const uploadDir = process.env.UPLOAD_DIR ?? path.resolve(process.cwd(), 'uploads');
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}

export const env = {
  nodeEnv: process.env.NODE_ENV ?? 'development',
  port: Number(process.env.PORT ?? 4000),
  sqlitePath: process.env.SQLITE_PATH ?? ':memory:',
  uploadDir,
  pythonBin: process.env.PYTHON_BIN ?? 'python3',
  pythonAgentScript:
    process.env.PYTHON_AGENT_SCRIPT ?? path.resolve(process.cwd(), 'backend', 'run_pipeline_cli.py'),
  pythonAgentTimeoutMs: Number(process.env.PYTHON_AGENT_TIMEOUT_MS ?? 120_000),
  pythonDebateRounds: Number(process.env.PYTHON_DEBATE_ROUNDS ?? 3),
  pythonDebateDisabled: process.env.PYTHON_DEBATE_DISABLED === 'true',
};
