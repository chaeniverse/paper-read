import { neon } from "@neondatabase/serverless";

// Single continuous note, iPhone-Notes style. One row keyed by NOTE_ID.
export const NOTE_ID = "paper-read-main";

// The Neon (Vercel Postgres) integration exposes the connection string as
// DATABASE_URL; the legacy Vercel Postgres integration used POSTGRES_URL.
function client() {
  const url = process.env.DATABASE_URL || process.env.POSTGRES_URL;
  if (!url) throw new Error("No database connection string set (DATABASE_URL).");
  return neon(url);
}

let ready: Promise<void> | null = null;

// Lazily ensure the notes table exists (runs once per server instance).
function ensureTable() {
  if (!ready) {
    const sql = client();
    ready = sql`
      CREATE TABLE IF NOT EXISTS notes (
        id TEXT PRIMARY KEY,
        body TEXT NOT NULL DEFAULT '',
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
      )
    `.then(() => undefined);
  }
  return ready;
}

export async function getNote(id: string = NOTE_ID): Promise<string> {
  const sql = client();
  await ensureTable();
  const rows = (await sql`SELECT body FROM notes WHERE id = ${id}`) as { body: string }[];
  return rows[0]?.body ?? "";
}

export async function saveNote(body: string, id: string = NOTE_ID): Promise<void> {
  const sql = client();
  await ensureTable();
  await sql`
    INSERT INTO notes (id, body, updated_at)
    VALUES (${id}, ${body}, now())
    ON CONFLICT (id) DO UPDATE SET body = EXCLUDED.body, updated_at = now()
  `;
}
