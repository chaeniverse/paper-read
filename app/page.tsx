import { items, type Item } from "@/lib/paper";
import Figure from "@/components/Figure";

export default function Page() {
  return (
    <main className="paper">
      <article>
        {items.map((it, i) => renderItem(it, i))}
      </article>
    </main>
  );
}

function renderItem(it: Item, i: number) {
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
          src={`/figures/${it.src}`}
          label={`Figure ${it.num}`}
        />
      );
    case "table":
      return (
        <Figure
          key={i}
          src={`/figures/${it.src}`}
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
