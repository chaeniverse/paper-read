import { NextResponse } from "next/server";
import { getNote, saveNote } from "@/lib/db";
import { slugs } from "@/lib/paper";

export const dynamic = "force-dynamic";

const valid = (id: unknown): id is string =>
  typeof id === "string" && slugs.includes(id);

// Returns the note body for a given paper (?id=<slug>).
// Degrades gracefully (empty note) if the DB is not configured yet.
export async function GET(req: Request) {
  const id = new URL(req.url).searchParams.get("id");
  if (!valid(id)) {
    return NextResponse.json({ body: "", error: "unknown_paper" }, { status: 400 });
  }
  try {
    const body = await getNote(id);
    return NextResponse.json({ body });
  } catch (err: any) {
    return NextResponse.json(
      { body: "", error: err?.message ?? "db_unavailable" },
      { status: 200 }
    );
  }
}

// Auto-save: upsert the note body for a paper. No explicit "save" button.
export async function PUT(req: Request) {
  try {
    const { id, body } = await req.json();
    if (!valid(id)) {
      return NextResponse.json({ ok: false, error: "unknown_paper" }, { status: 400 });
    }
    await saveNote(typeof body === "string" ? body : "", id);
    return NextResponse.json({ ok: true });
  } catch (err: any) {
    return NextResponse.json(
      { ok: false, error: err?.message ?? "save_failed" },
      { status: 500 }
    );
  }
}
