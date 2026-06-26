import raw from "@/data/paper.json";

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

export const items = raw.items as Item[];

export const paperTitle =
  (items.find((i) => i.type === "title") as { text: string } | undefined)?.text ??
  "Paper";
