"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Status = "idle" | "saving" | "saved" | "error";

export default function NotesWidget({
  paperSlug,
  paperTitle,
}: {
  paperSlug: string;
  paperTitle?: string;
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [loaded, setLoaded] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const taRef = useRef<HTMLTextAreaElement | null>(null);
  const url = `/api/note?id=${encodeURIComponent(paperSlug)}`;

  // Load the saved note the first time the pad is opened.
  useEffect(() => {
    if (!open || loaded) return;
    let alive = true;
    fetch(url)
      .then((r) => r.json())
      .then((d) => {
        if (!alive) return;
        setText(d.body ?? "");
        setLoaded(true);
        setTimeout(() => taRef.current?.focus(), 50);
      })
      .catch(() => setLoaded(true));
    return () => {
      alive = false;
    };
  }, [open, loaded]);

  const save = useCallback(
    async (body: string) => {
      setStatus("saving");
      try {
        const r = await fetch("/api/note", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: paperSlug, body }),
        });
        setStatus(r.ok ? "saved" : "error");
      } catch {
        setStatus("error");
      }
    },
    [paperSlug]
  );

  // Debounced auto-save on every keystroke. No save button.
  const onChange = (v: string) => {
    setText(v);
    setStatus("saving");
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => save(v), 600);
  };

  // Flush a pending save when leaving the page.
  useEffect(() => {
    const flush = () => {
      if (timer.current) {
        clearTimeout(timer.current);
        navigator.sendBeacon?.(
          "/api/note",
          new Blob([JSON.stringify({ id: paperSlug, body: text })], {
            type: "application/json",
          })
        );
      }
    };
    window.addEventListener("beforeunload", flush);
    return () => window.removeEventListener("beforeunload", flush);
  }, [text, paperSlug]);

  const close = () => {
    if (timer.current) {
      clearTimeout(timer.current);
      save(text);
    }
    setOpen(false);
  };

  return (
    <>
      {!open && (
        <button
          className="note-fab"
          onClick={() => setOpen(true)}
          aria-label="Open notes"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 4h11l5 5v11a0 0 0 0 1 0 0H4a0 0 0 0 1 0 0V4z" />
            <path d="M15 4v5h5" />
            <path d="M8 13h8M8 17h5" />
          </svg>
        </button>
      )}

      {open && (
        <div className="note-pad" role="dialog" aria-label="Notes">
          <div className="note-head">
            <div className="note-head-left">
              <span className="note-dot" data-status={status} />
              <span className="note-status">
                {status === "saving"
                  ? "저장 중…"
                  : status === "error"
                  ? "저장 실패"
                  : status === "saved"
                  ? "저장됨"
                  : paperTitle || "메모"}
              </span>
            </div>
            <button className="note-close" onClick={close} aria-label="Close notes">
              ✕
            </button>
          </div>
          <textarea
            ref={taRef}
            className="note-area"
            value={text}
            placeholder={loaded ? "여기에 메모하세요… 자동 저장됩니다." : "불러오는 중…"}
            onChange={(e) => onChange(e.target.value)}
            spellCheck={false}
          />
        </div>
      )}
    </>
  );
}
