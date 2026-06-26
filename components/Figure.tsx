"use client";

import { useEffect, useRef, useState } from "react";

export default function Figure({
  src,
  label,
  variant = "figure",
}: {
  src: string;
  label: string;
  variant?: "figure" | "equation";
}) {
  const [open, setOpen] = useState(false);

  if (variant === "equation") {
    return (
      <div className="eq">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={src} alt={label} loading="lazy" onClick={() => setOpen(true)} />
        {open && <Lightbox src={src} label={label} onClose={() => setOpen(false)} />}
      </div>
    );
  }

  return (
    <figure className="fig">
      <div className="fig-frame">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={src} alt={label} loading="lazy" />
        <button
          className="zoom-btn"
          onClick={() => setOpen(true)}
          aria-label={`Zoom ${label}`}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
            <circle cx="11" cy="11" r="7" />
            <line x1="16.5" y1="16.5" x2="21" y2="21" />
            <line x1="11" y1="8" x2="11" y2="14" />
            <line x1="8" y1="11" x2="14" y2="11" />
          </svg>
          Zoom
        </button>
      </div>
      {open && <Lightbox src={src} label={label} onClose={() => setOpen(false)} />}
    </figure>
  );
}

function Lightbox({
  src,
  label,
  onClose,
}: {
  src: string;
  label: string;
  onClose: () => void;
}) {
  const [scale, setScale] = useState(1);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "+" || e.key === "=") setScale((s) => clamp(s + 0.4));
      if (e.key === "-") setScale((s) => clamp(s - 0.4));
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  const clamp = (s: number) => Math.min(6, Math.max(1, Math.round(s * 10) / 10));

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    setScale((s) => clamp(s + (e.deltaY < 0 ? 0.3 : -0.3)));
  };

  const onDown = (e: React.MouseEvent) => {
    if (scale <= 1) return;
    drag.current = { x: e.clientX, y: e.clientY, ox: pos.x, oy: pos.y };
  };
  const onMove = (e: React.MouseEvent) => {
    if (!drag.current) return;
    setPos({
      x: drag.current.ox + (e.clientX - drag.current.x),
      y: drag.current.oy + (e.clientY - drag.current.y),
    });
  };
  const onUp = () => (drag.current = null);

  const reset = () => {
    setScale(1);
    setPos({ x: 0, y: 0 });
  };

  return (
    <div className="lightbox" onClick={onClose} role="dialog" aria-label={label}>
      <div className="lb-bar" onClick={(e) => e.stopPropagation()}>
        <span className="lb-label">{label}</span>
        <div className="lb-tools">
          <button onClick={() => setScale((s) => clamp(s - 0.4))} aria-label="Zoom out">−</button>
          <span className="lb-scale">{Math.round(scale * 100)}%</span>
          <button onClick={() => setScale((s) => clamp(s + 0.4))} aria-label="Zoom in">+</button>
          <button onClick={reset} className="lb-reset">Reset</button>
          <button onClick={onClose} className="lb-close" aria-label="Close">✕</button>
        </div>
      </div>
      <div
        className="lb-stage"
        onWheel={onWheel}
        onMouseDown={onDown}
        onMouseMove={onMove}
        onMouseUp={onUp}
        onMouseLeave={onUp}
        onClick={(e) => e.stopPropagation()}
        style={{ cursor: scale > 1 ? (drag.current ? "grabbing" : "grab") : "zoom-in" }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt={label}
          draggable={false}
          onClick={() => scale <= 1 && setScale(2.2)}
          style={{
            transform: `translate(${pos.x}px, ${pos.y}px) scale(${scale})`,
          }}
        />
      </div>
    </div>
  );
}
