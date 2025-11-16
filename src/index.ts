import { createApp } from './app';
import { env } from './config/env';
import './db/connection';

const app = createApp();

app.listen(env.port, () => {
  console.log(`Medical Bill Fighter API running on port ${env.port}`);
});
