#!/usr/bin/env python3
"""Extract a paper PDF into data/paper.json + public/figures/*.png.

Body text is pulled in reading order; FIGURE/TABLE regions (mostly vector
graphics) are rendered to high-resolution PNGs and placed inline at the
first in-text reference.

Usage:
    pip install pymupdf
    python scripts/extract.py "sources/<file>.pdf"
"""
import sys, os, re, json
import fitz  # PyMuPDF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG_DIR = os.path.join(ROOT, "public", "figures")
DATA = os.path.join(ROOT, "data", "paper.json")
CONTENT_TOP = 78  # px from page top to skip running header
SCALE = 3         # figure render scale


def block_text(b):
    out = []
    for l in b["lines"]:
        out.append("".join(s["text"] for s in l["spans"]))
    s = ""
    for i, lt in enumerate(out):
        if i == 0:
            s = lt
        elif s.endswith("-"):      # de-hyphenate line wraps
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


def main(pdf_path):
    os.makedirs(FIG_DIR, exist_ok=True)
    d = fitz.open(pdf_path)
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
                os.path.join(FIG_DIR, f"fig{n}.png"))
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
                    os.path.join(FIG_DIR, f"table{n}.png"))
                tablemap[n] = f"table{n}.png"

    # ---- page 0: title / authors / abstract / keywords ----
    items = []
    pg = d[0]
    p0 = [b for b in pg.get_text("dict")["blocks"] if "lines" in b]
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
            if re.match(r"^\d{3,4} AUSTIN et al", t) or re.match(r"^AUSTIN et al", t):
                continue
            if re.match(r"^\d{3,4}$", t) or "Downloaded from" in t or "Creative Commons" in t:
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

    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    json.dump({"items": items}, open(DATA, "w"), ensure_ascii=False, indent=1)
    print(f"figures={sorted(figmap)} tables={sorted(tablemap)} items={len(items)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python scripts/extract.py <pdf>")
    main(sys.argv[1])
