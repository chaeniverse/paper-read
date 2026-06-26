#!/usr/bin/env python3
"""Extract a paper PDF into data/papers/<slug>.json + public/figures/<slug>/*.png.

Body text is pulled in reading order; FIGURE/TABLE regions (mostly vector
graphics) are rendered to high-resolution PNGs and placed inline at the
first in-text reference. Repeated running heads/footers are detected and
dropped automatically. The papers index (data/papers.index.ts) is rebuilt
so new papers show up on the home page with no manual wiring.

Usage:
    pip install pymupdf
    python scripts/extract.py "sources/<file>.pdf" [slug] \
        [--venue "Statistics in Medicine"] [--year 2020]
"""
import sys, os, re, json, shutil
import fitz  # PyMuPDF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPERS_DIR = os.path.join(ROOT, "data", "papers")
INDEX_TS = os.path.join(ROOT, "data", "papers.index.ts")
CONTENT_TOP = 78  # px from page top to skip running header
SCALE = 3         # figure render scale


def slugify(name):
    s = re.sub(r"\.pdf$", "", os.path.basename(name), flags=re.I)
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return re.sub(r"-+", "-", s)[:60] or "paper"


def block_text(b):
    out = ["".join(s["text"] for s in l["spans"]) for l in b["lines"]]
    s = ""
    for i, lt in enumerate(out):
        if i == 0:
            s = lt
        elif s.endswith("-"):          # de-hyphenate line wraps
            s = s[:-1] + lt
        else:
            s = s + " " + lt
    s = s.replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()


def maxsize(b):
    return max(s["size"] for l in b["lines"] for s in l["spans"])


def refs_in(text, label):
    nums = set()
    for m in re.finditer(r"%s[s]?\s*((?:\d+\s*(?:to|through|[-,]|and)\s*)*\d+)" % label, text):
        seg = m.group(1)
        for r in re.finditer(r"(\d+)\s*(?:to|through|-)\s*(\d+)", seg):
            nums.update(range(int(r.group(1)), int(r.group(2)) + 1))
        for n in re.findall(r"\d+", seg):
            nums.add(int(n))
    return nums


def place(items, mp, kind, label):
    placed, out = set(), []
    for it in items:
        out.append(it)
        if it.get("type") == "p":
            for n in refs_in(it["text"], label):
                if n in mp and n not in placed:
                    out.append({"type": kind, "num": n, "src": mp[n]})
                    placed.add(n)
    for n in sorted(mp):                     # chain unreferenced after n-1
        if n in placed:
            continue
        ins = {"type": kind, "num": n, "src": mp[n]}
        pos = next((i for i, it in enumerate(out)
                    if it.get("type") == kind and it.get("num") == n - 1), None)
        out.insert(pos + 1, ins) if pos is not None else out.append(ins)
        placed.add(n)
    return out


def boilerplate_lines(doc):
    """Header/footer lines that repeat near the top/bottom across pages."""
    from collections import Counter
    c = Counter()
    for pg in doc:
        h = pg.rect.height
        for b in pg.get_text("dict")["blocks"]:
            if "lines" not in b:
                continue
            y0, y1 = b["bbox"][1], b["bbox"][3]
            if y0 < 70 or y1 > h - 60:
                t = block_text(b)
                key = re.sub(r"\d+", "#", t)        # ignore page numbers
                if 0 < len(t) < 90:
                    c[key] += 1
    return {k for k, v in c.items() if v >= 3}


def main(pdf_path, slug, venue, year):
    fig_dir = os.path.join(ROOT, "public", "figures", slug)
    os.makedirs(fig_dir, exist_ok=True)
    os.makedirs(PAPERS_DIR, exist_ok=True)
    d = fitz.open(pdf_path)
    boiler = boilerplate_lines(d)
    figmap, tablemap = {}, {}

    # ---- figures (caption below) & tables (caption above) ----
    for pg in d:
        blocks = [b for b in pg.get_text("dict")["blocks"] if "lines" in b]
        fcaps = []
        for b in blocks:
            t = "".join(s["text"] for l in b["lines"] for s in l["spans"])
            m = re.match(r"^F\s?I\s?G\s?U\s?R\s?E\s?(\d+)", t)
            if m:
                fcaps.append((b["bbox"][1], b["bbox"][3], int(m.group(1))))
        fcaps.sort()
        prev = CONTENT_TOP
        for y0, y1, n in fcaps:
            clip = fitz.Rect(40, prev, 555, y1 + 3)
            pg.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE), clip=clip).save(
                os.path.join(fig_dir, f"fig{n}.png"))
            figmap[n] = f"fig{n}.png"
            prev = y1 + 3
        for b in blocks:
            t = "".join(s["text"] for l in b["lines"] for s in l["spans"])
            m = re.match(r"^T\s?A\s?B\s?L\s?E\s?(\d+)", t)
            if m:
                n = int(m.group(1)); cap_y0 = b["bbox"][1]
                data = [bb for bb in blocks
                        if bb["bbox"][1] >= cap_y0 - 1 and abs(maxsize(bb) - 8.5) < 0.4]
                bottom = max([bb["bbox"][3] for bb in data] + [b["bbox"][3]])
                clip = fitz.Rect(40, cap_y0 - 3, 560, bottom + 4)
                pg.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE), clip=clip).save(
                    os.path.join(fig_dir, f"table{n}.png"))
                tablemap[n] = f"table{n}.png"

    # ---- page 0: title / authors / abstract / keywords ----
    items = []
    p0 = [b for b in d[0].get_text("dict")["blocks"] if "lines" in b]
    abst = []
    for b in sorted(p0, key=lambda b: b["bbox"][1]):
        sz, t = maxsize(b), block_text(b)
        if not t:
            continue
        if sz >= 17:
            items.append({"type": "title", "text": t})
        elif 11.5 < sz < 13 and not re.match(r"^\d+\s*INTRODUCTION", t, re.I):
            items.append({"type": "authors",
                          "text": re.sub(r"(?<=[a-zA-Z])\d[\d,]*", "", t).replace("  ", " ").strip()})
        elif abs(sz - 10) < 0.4:
            abst.append(re.sub(r"^Abstract", "", t).strip())
    keyw = None
    for i, b in enumerate(p0):
        if "K E Y W O R D S" in "".join(s["text"] for l in b["lines"] for s in l["spans"]):
            if i + 1 < len(p0):
                keyw = block_text(p0[i + 1])
    if abst:
        items.append({"type": "abstract", "text": " ".join(abst)})
    if keyw:
        items.append({"type": "keywords", "text": keyw})

    # ---- body: headings + paragraphs ----
    for i, pg in enumerate(d):
        rows = []
        for b in pg.get_text("dict")["blocks"]:
            if "lines" not in b or b["bbox"][0] > 560:
                continue
            sz, t = maxsize(b), block_text(b)
            if not t:
                continue
            if re.match(r"^F\s?I\s?G\s?U\s?R\s?E", t) or re.match(r"^T\s?A\s?B\s?L\s?E\s?\d", t):
                continue
            if re.sub(r"\d+", "#", t) in boiler:
                continue
            if re.match(r"^\d{1,4}$", t) or "Downloaded from" in t or "Creative Commons" in t:
                continue
            if "wileyonlinelibrary.com/journal" in t or re.match(r"^(R E S E A R C H|RESEARCH)", t):
                continue
            rows.append((b["bbox"][1], sz, t))
        for _, sz, t in sorted(rows):
            if i == 0 and (sz >= 11.5 and not re.match(r"^\d+\s*INTRODUCTION", t, re.I)):
                continue
            if i == 0 and abs(sz - 10) < 0.4:
                continue
            if abs(sz - 8.5) < 0.4 or sz < 7.5 or abs(sz - 7) < 0.4 or abs(sz - 8) < 0.5:
                continue
            if sz >= 11.5:
                m = re.match(r"^(\d+(?:\.\d+)*)\s*(.+)$", t)
                if m:
                    lvl = "h2" if "." not in m.group(1) else "h3"
                    items.append({"type": lvl, "num": m.group(1), "text": m.group(2)})
                else:
                    items.append({"type": "h2", "num": "", "text": t})
            else:
                items.append({"type": "p", "text": t})

    items = place(items, figmap, "figure", "Figure")
    items = place(items, tablemap, "table", "Table")

    def first(t):
        return next((it["text"] for it in items if it.get("type") == t), "")

    # serve the original PDF from /public/pdfs/<slug>.pdf
    pdf_out_dir = os.path.join(ROOT, "public", "pdfs")
    os.makedirs(pdf_out_dir, exist_ok=True)
    shutil.copyfile(pdf_path, os.path.join(pdf_out_dir, f"{slug}.pdf"))

    paper = {
        "slug": slug,
        "title": first("title"),
        "authors": first("authors"),
        "venue": venue,
        "year": year,
        "abstract": first("abstract"),
        "pdf": f"{slug}.pdf",
        "items": items,
    }
    json.dump(paper, open(os.path.join(PAPERS_DIR, f"{slug}.json"), "w"),
              ensure_ascii=False, indent=1)
    rebuild_index()
    print(f"[{slug}] figures={sorted(figmap)} tables={sorted(tablemap)} items={len(items)}")


def rebuild_index():
    files = sorted(f[:-5] for f in os.listdir(PAPERS_DIR) if f.endswith(".json"))
    lines = ["// AUTO-GENERATED by scripts/extract.py — lists every paper JSON.",
             "// You can also edit by hand: add an import and include it in `papersData`.",
             ""]
    var = {}
    for s in files:
        v = re.sub(r"[^a-zA-Z0-9]", "_", s)
        v = re.sub(r"_(\w)", lambda m: m.group(1).upper(), "_" + v)
        var[s] = v
        lines.append(f'import {v} from "./papers/{s}.json";')
    lines.append("")
    lines.append("export const papersData = [" + ", ".join(var[s] for s in files) + "];")
    lines.append("")
    open(INDEX_TS, "w").write("\n".join(lines))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    if not args:
        sys.exit('usage: python scripts/extract.py <pdf> [slug] [--venue "X"] [--year N]')
    pdf = args[0]
    venue, year, slug = None, None, None
    rest = args[1:]
    i = 0
    while i < len(rest):
        if rest[i] == "--venue":
            venue = rest[i + 1]; i += 2
        elif rest[i] == "--year":
            year = int(rest[i + 1]); i += 2
        else:
            slug = rest[i]; i += 1
    slug = slug or slugify(pdf)
    main(pdf, slug, venue, year)
