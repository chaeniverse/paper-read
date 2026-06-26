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
  | { type: "table"; num: number; src: string };

export type Paper = {
  slug: string;
  title: string;
  authors: string;
  venue?: string;
  year?: number;
  abstract?: string;
  pdf?: string; // filename under /public/pdfs
  items: Item[];
};

// All papers, newest first (by year, then title).
export const papers: Paper[] = (papersData as Paper[])
  .slice()
  .sort((a, b) => (b.year ?? 0) - (a.year ?? 0) || a.title.localeCompare(b.title));

export function getPaper(slug: string): Paper | undefined {
  return (papersData as Paper[]).find((p) => p.slug === slug);
}

export const slugs = (papersData as Paper[]).map((p) => p.slug);
