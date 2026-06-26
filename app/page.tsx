import Link from "next/link";
import { papers, references, type Paper } from "@/lib/paper";
import PdfIcon from "@/components/PdfIcon";

export default function Home() {
  return (
    <main className="index">
      <header className="index-head">
        <h1>Paper Read</h1>
        <p>읽은 논문과 메모를 모아두는 곳. 제목을 누르면 논문을 펼쳐 읽으며 바로 메모할 수 있어요.</p>
      </header>

      <ul className="post-list">
        {papers.map((p) => (
          <PaperCard key={p.slug} p={p} />
        ))}
      </ul>

      {references.length > 0 && (
        <section className="refs">
          <h2 className="refs-head">참고자료 · 패키지 매뉴얼</h2>
          <ul className="ref-list">
            {references.map((p) => (
              <li key={p.slug} className="ref">
                <a
                  className="ref-link"
                  href={`/pdfs/${p.pdf}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <PdfIcon size={16} />
                  <span className="ref-title">{p.title}</span>
                  {p.venue ? <span className="ref-venue">{p.venue}</span> : null}
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      {papers.length === 0 && references.length === 0 && (
        <p className="empty">아직 논문이 없습니다. <code>scripts/extract.py</code>로 추가하세요.</p>
      )}
    </main>
  );
}

function PaperCard({ p }: { p: Paper }) {
  const figs = p.items.filter((i) => i.type === "figure").length;
  return (
    <li className="post">
      <Link href={`/paper/${p.slug}`} className="post-link">
        <div className="post-meta">
          {p.venue ? <span>{p.venue}</span> : null}
          {p.year ? <span>{p.year}</span> : null}
          {figs ? <span>{figs} figures</span> : null}
        </div>
        <h2 className="post-title">{p.title}</h2>
        <p className="post-authors">{p.authors}</p>
        {p.abstract ? <p className="post-excerpt">{excerpt(p.abstract)}</p> : null}
      </Link>
      <div className="post-actions">
        <Link href={`/paper/${p.slug}`} className="post-cta">읽기 →</Link>
        {p.pdf ? (
          <a
            className="pdf-chip"
            href={`/pdfs/${p.pdf}`}
            target="_blank"
            rel="noopener noreferrer"
            title="원본 PDF 열기"
          >
            <PdfIcon /> PDF
          </a>
        ) : null}
      </div>
    </li>
  );
}

function excerpt(s: string, n = 220) {
  return s.length > n ? s.slice(0, n).trimEnd() + "…" : s;
}
