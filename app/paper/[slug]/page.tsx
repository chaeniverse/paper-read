import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { getPaper, slugs, isReadable, type Item, type Paper } from "@/lib/paper";
import Figure from "@/components/Figure";
import NotesWidget from "@/components/NotesWidget";
import PdfIcon from "@/components/PdfIcon";

export function generateStaticParams() {
  return slugs.map((slug) => ({ slug }));
}

export function generateMetadata({ params }: { params: { slug: string } }) {
  const p = getPaper(params.slug);
  return { title: p ? p.title : "Paper" };
}

export default function PaperPage({ params }: { params: { slug: string } }) {
  const paper = getPaper(params.slug);
  if (!paper) notFound();
  // Reference-only PDFs have no reading view — send straight to the file.
  if (!isReadable(paper) && paper.pdf) redirect(`/pdfs/${paper.pdf}`);

  return (
    <main className="paper">
      <div className="paper-bar">
        <Link href="/" className="back-link">← 목록</Link>
        {paper.pdf ? (
          <a
            className="pdf-chip"
            href={`/pdfs/${paper.pdf}`}
            target="_blank"
            rel="noopener noreferrer"
            title="원본 PDF 열기"
          >
            <PdfIcon /> 원본 PDF
          </a>
        ) : null}
      </div>
      <article>
        {paper.items.map((it, i) => renderItem(it, i, paper))}
      </article>
      <NotesWidget paperSlug={paper.slug} paperTitle={paper.title} />
    </main>
  );
}

function renderItem(it: Item, i: number, paper: Paper) {
  switch (it.type) {
    case "title":
      return <h1 key={i} className="paper-title">{it.text}</h1>;
    case "authors":
      return <p key={i} className="authors">{it.text}</p>;
    case "abstract":
      return (
        <section key={i} className="abstract">
          <h2 className="abstract-label">Abstract</h2>
          <p>{it.text}</p>
        </section>
      );
    case "keywords":
      return (
        <p key={i} className="keywords">
          <span>KEYWORDS</span> {it.text}
        </p>
      );
    case "h2":
      return (
        <h2 key={i} className="sec" id={`sec-${it.num ?? i}`}>
          {it.num ? <span className="sec-num">{it.num}</span> : null}
          {titleCase(it.text)}
        </h2>
      );
    case "h3":
      return (
        <h3 key={i} className="subsec">
          {it.num ? <span className="sec-num">{it.num}</span> : null}
          {it.text}
        </h3>
      );
    case "figure":
      return (
        <Figure
          key={i}
          src={`/figures/${paper.slug}/${it.src}`}
          label={`Figure ${it.num}`}
        />
      );
    case "table":
      return (
        <Figure
          key={i}
          src={`/figures/${paper.slug}/${it.src}`}
          label={`Table ${it.num}`}
        />
      );
    case "p":
      return <p key={i}>{it.text}</p>;
    default:
      return null;
  }
}

// Section headings are stored in ALL CAPS in the PDF; soften to Title Case.
function titleCase(s: string) {
  if (s !== s.toUpperCase()) return s;
  const small = new Set(["and", "or", "for", "the", "of", "to", "a", "an", "in", "on", "with"]);
  return s
    .toLowerCase()
    .split(/\s+/)
    .map((w, idx) =>
      idx > 0 && small.has(w) ? w : w.charAt(0).toUpperCase() + w.slice(1)
    )
    .join(" ");
}
