import Database from 'better-sqlite3';
import type BetterSqlite3 from 'better-sqlite3';
import { env } from '../config/env';
import { applyMigrations } from './schema';

const db: BetterSqlite3.Database = new Database(env.sqlitePath, {
  verbose: env.nodeEnv === 'development' ? console.log : undefined,
});

db.pragma('foreign_keys = ON');
applyMigrations(db);

export { db };
