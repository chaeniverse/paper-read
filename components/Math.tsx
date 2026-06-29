"use client";

import { useEffect, useMemo, useRef } from "react";
import katex from "katex";

// Mathpix/Marker occasionally wrap code or prose in $...$. Feeding that to KaTeX
// is wrong (and pathological inputs can stall it), so detect non-math and show
// it as plain text instead.
const NOT_MATH =
  /#{3,}|<-|[A-Za-z]\w*\s*=\s*(NA|TRUE|FALSE|NULL|"|F\b|T\b)|\b(axes|xlab|ylab|lwd|axis|par|plot|points|lines|main)\s*[=(]/;

function isMath(tex: string): boolean {
  return tex.length <= 400 && !NOT_MATH.test(tex);
}

// Render KaTeX into an element on the CLIENT only (after mount). Keeping katex out
// of server-side prerendering makes the build fast and immune to slow inputs.
function useKatex(tex: string, displayMode: boolean) {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (!isMath(tex)) {
      el.textContent = tex;
      return;
    }
    try {
      katex.render(tex, el, {
        displayMode,
        throwOnError: false,
        strict: false,
        trust: true,
        maxExpand: 1000,
      });
    } catch {
      el.textContent = tex;
    }
  }, [tex, displayMode]);
  return ref;
}

// A display equation, optionally numbered.
export function MathBlock({ tex, num }: { tex: string; num?: string }) {
  const ref = useKatex(tex, true);
  return (
    <div className="math-block">
      <span className="math-render" ref={ref}>{tex}</span>
      {num ? <span className="math-num">({num})</span> : null}
    </div>
  );
}

function MathInline({ tex }: { tex: string }) {
  const ref = useKatex(tex, false);
  return <span className="math-render" ref={ref}>{tex}</span>;
}

const MATH_RE =
  /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)|\$((?:\\.|[^$])+?)\$/g;

// Render a paragraph string that may contain inline (and stray display) math.
export function MathText({ text }: { text: string }) {
  const parts = useMemo(() => splitMath(text), [text]);
  return (
    <>
      {parts.map((p, i) =>
        p.tex == null ? (
          <span key={i}>{p.text}</span>
        ) : p.display ? (
          <MathBlock key={i} tex={p.tex} />
        ) : (
          <MathInline key={i} tex={p.tex} />
        )
      )}
    </>
  );
}

// An OCR'd table (HTML). Cells may contain $...$ math, rendered on the client.
export function TableHtml({ html }: { html: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.querySelectorAll<HTMLElement>("td, th").forEach((cell) => {
      const t = cell.textContent ?? "";
      if (!t.includes("$")) return;
      cell.innerHTML = t.replace(MATH_RE, (m, dd, br, pr, in1) => {
        const tex = (dd ?? br ?? pr ?? in1 ?? "").trim();
        if (!isMath(tex)) return m;
        try {
          return katex.renderToString(tex, {
            displayMode: false,
            throwOnError: false,
            strict: false,
            trust: true,
            maxExpand: 1000,
          });
        } catch {
          return m;
        }
      });
    });
  }, [html]);
  return (
    <div ref={ref} className="table-html" dangerouslySetInnerHTML={{ __html: html }} />
  );
}

type Seg = { text: string; tex?: undefined } | { text?: undefined; tex: string; display: boolean };

function splitMath(text: string): Seg[] {
  const out: Seg[] = [];
  let last = 0;
  for (const m of text.matchAll(MATH_RE)) {
    const idx = m.index ?? 0;
    if (idx > last) out.push({ text: text.slice(last, idx) });
    const display = m[1] != null || m[2] != null;
    const tex = (m[1] ?? m[2] ?? m[3] ?? m[4] ?? "").trim();
    out.push({ tex, display });
    last = idx + m[0].length;
  }
  if (last < text.length) out.push({ text: text.slice(last) });
  return out;
}
