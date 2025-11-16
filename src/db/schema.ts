import type BetterSqlite3 from 'better-sqlite3';

const baseStatements = [
  `CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_name TEXT,
    provider_name TEXT,
    status TEXT DEFAULT 'pending',
    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    original_filename TEXT,
    notes TEXT,
    prompt TEXT,
    file_path TEXT,
    ocr_text TEXT
  );`,
  `CREATE TABLE IF NOT EXISTS line_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL,
    description TEXT,
    code TEXT,
    quantity INTEGER DEFAULT 1,
    amount REAL DEFAULT 0,
    flags TEXT,
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE
  );`,
  `CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL,
    avg_cost REAL,
    actual_cost REAL,
    summary_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE
  );`,
  `CREATE TABLE IF NOT EXISTS scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL,
    negotiation_email TEXT,
    phone_script TEXT,
    alternatives_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE
  );`,
  `CREATE TABLE IF NOT EXISTS agent_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL,
    transcript_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE
  );`
];

const ensureColumn = (
  db: BetterSqlite3.Database,
  table: string,
  column: string,
  definition: string
) => {
  const columns = db.prepare(`PRAGMA table_info(${table})`).all() as Array<{ name: string }>;
  const exists = columns.some((col) => col.name === column);
  if (!exists) {
    db.prepare(`ALTER TABLE ${table} ADD COLUMN ${definition}`).run();
  }
};

export const applyMigrations = (db: BetterSqlite3.Database): void => {
  baseStatements.forEach((statement) => {
    db.prepare(statement).run();
  });

  ensureColumn(db, 'bills', 'prompt', 'TEXT');
  ensureColumn(db, 'bills', 'file_path', 'TEXT');
  ensureColumn(db, 'bills', 'ocr_text', 'TEXT');
};
