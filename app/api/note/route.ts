import { NextResponse } from "next/server";
import { getNote, saveNote } from "@/lib/db";

export const dynamic = "force-dynamic";

// Returns the current note body. If the DB is not configured yet,
// degrade gracefully so the UI still loads (empty note).
export async function GET() {
  try {
    const body = await getNote();
    return NextResponse.json({ body });
  } catch (err: any) {
    return NextResponse.json(
      { body: "", error: err?.message ?? "db_unavailable" },
      { status: 200 }
    );
  }
}

// Auto-save: upsert the note body. No explicit "save" button on the client.
export async function PUT(req: Request) {
  try {
    const { body } = await req.json();
    await saveNote(typeof body === "string" ? body : "");
    return NextResponse.json({ ok: true });
  } catch (err: any) {
    return NextResponse.json(
      { ok: false, error: err?.message ?? "save_failed" },
      { status: 500 }
    );
  }
}
