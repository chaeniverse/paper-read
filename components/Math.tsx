"use client";

import { useEffect, useMemo, useRef } from "react";
import katex from "katex";
import renderMathInElement from "katex/contrib/auto-render";

function render(tex: string, displayMode: boolean): string {
  try {
    return katex.renderToString(tex, {
      displayMode,
      throwOnError: false,
      strict: false,
      trust: true,
      output: "html",
    });
  } catch {
    // Fall back to the raw TeX so nothing disappears on a parse error.
    return displayMode ? `\\[${tex}\\]` : `\\(${tex}\\)`;
  }
}

// A display equation rendered on its own line, optionally numbered.
export function MathBlock({ tex, num }: { tex: string; num?: string }) {
  const html = useMemo(() => render(tex, true), [tex]);
  return (
    <div className="math-block">
      <span
        className="math-render"
        dangerouslySetInnerHTML={{ __html: html }}
      />
      {num ? <span className="math-num">({num})</span> : null}
    </div>
  );
}

// An OCR'd table (HTML). Cells may contain $...$ / $$...$$ math, which we
// render in place with KaTeX's auto-render after mount.
export function TableHtml({ html }: { html: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    try {
      renderMathInElement(ref.current, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
        ],
        throwOnError: false,
      });
    } catch {
      /* leave raw text on failure */
    }
  }, [html]);
  return (
    <div
      ref={ref}
      className="table-html"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

// Inline math segment.
function MathInline({ tex }: { tex: string }) {
  const html = useMemo(() => render(tex, false), [tex]);
  return (
    <span className="math-render" dangerouslySetInnerHTML={{ __html: html }} />
  );
}

// Matches inline ( \(...\)  or  $...$ ) and display ( \[...\] or $$...$$ ) math.
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

type Seg = { text: string; tex?: undefined } | { text?: undefined; tex: string; display: boolean };

function splitMath(text: string): Seg[] {
  const out: Seg[] = [];
  let last = 0;
  for (const m of text.matchAll(MATH_RE)) {
    const idx = m.index ?? 0;
    if (idx > last) out.push({ text: text.slice(last, idx) });
    const display = m[1] != null || m[2] != null; // $$...$$ or \[...\]
    const tex = (m[1] ?? m[2] ?? m[3] ?? m[4] ?? "").trim();
    out.push({ tex, display });
    last = idx + m[0].length;
  }
  if (last < text.length) out.push({ text: text.slice(last) });
  return out;
}
