import { papersData } from "@/data/papers.index";

export type Item =
  | { type: "title"; text: string }
  | { type: "authors"; text: string }
  | { type: "abstract"; text: string }
  | { type: "keywords"; text: string }
  | { type: "h2"; num?: string; text: string }
  | { type: "h3"; num?: string; text: string }
  | { type: "p"; text: string }
  | { type: "figure"; num: number; src: string }
  | { type: "table"; num: number; src: string }
  | { type: "equation"; src: string };

export type Paper = {
  slug: string;
  kind?: "paper" | "pdf"; // "pdf" = reference/manual, link-only (no reading view)
  title: string;
  authors: string;
  venue?: string;
  year?: number;
  abstract?: string;
  pdf?: string; // filename under /public/pdfs
  items: Item[];
};

const all = (papersData as Paper[]).slice();
const byRecency = (a: Paper, b: Paper) =>
  (b.year ?? 0) - (a.year ?? 0) || a.title.localeCompare(b.title);

export const isReadable = (p: Paper) => (p.kind ?? "paper") === "paper";

// Full papers (with a reading view) and reference-only PDFs, each newest first.
export const papers: Paper[] = all.filter(isReadable).sort(byRecency);
export const references: Paper[] = all.filter((p) => !isReadable(p)).sort(byRecency);

export function getPaper(slug: string): Paper | undefined {
  return all.find((p) => p.slug === slug);
}

// Only readable papers get a /paper/[slug] route.
export const slugs = papers.map((p) => p.slug);
