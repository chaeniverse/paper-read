#!/usr/bin/env python3
"""Extract a paper PDF into data/papers/<slug>.json + public/figures/<slug>/*.png.

Two modes:
  * paper  (default): reflow body text (1- or 2-column aware), render FIGURE/TABLE
            regions to high-res PNGs, place them inline at first reference.
  * --link-only:      register the PDF as a reference card only (no body reflow);
            just copies the PDF and writes metadata. Good for big manuals/vignettes.

The papers index (data/papers.index.ts) is rebuilt so new papers show up on the
home page with no manual wiring.

Usage:
    pip install pymupdf
    python scripts/extract.py "sources/<file>.pdf" <slug> \
        [--title "..."] [--authors "..."] [--venue "..."] [--year N] [--link-only]
"""
import sys, os, re, json, shutil
from collections import Counter
import fitz  # PyMuPDF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPERS_DIR = os.path.join(ROOT, "data", "papers")
PDF_DIR = os.path.join(ROOT, "public", "pdfs")
INDEX_TS = os.path.join(ROOT, "data", "papers.index.ts")
CONTENT_TOP = 70
SCALE = 3


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
        elif s.endswith("-"):
            s = s[:-1] + lt
        else:
            s = s + " " + lt
    return re.sub(r"\s+", " ", s.replace(" ", " ")).strip()


def maxsize(b):
    return max(s["size"] for l in b["lines"] for s in l["spans"])


# ---------- column-aware reading order ----------
def col_of(bbox, W):
    x0, x1 = bbox[0], bbox[2]
    if (x1 - x0) > 0.58 * W:
        return "full"
    return "L" if (x0 + x1) / 2 < W / 2 else "R"


def xrange_of(col, W):
    if col == "L":
        return (36, W / 2 + 8)
    if col == "R":
        return (W / 2 - 8, W - 30)
    return (32, W - 30)


def reading_order(blocks, W):
    blocks = sorted(blocks, key=lambda b: b["bbox"][1])
    out, buf = [], []

    def flush():
        L = [b for b in buf if col_of(b["bbox"], W) == "L"]
        R = [b for b in buf if col_of(b["bbox"], W) != "L"]
        out.extend(sorted(L, key=lambda b: b["bbox"][1]))
        out.extend(sorted(R, key=lambda b: b["bbox"][1]))
        buf.clear()

    for b in blocks:
        if col_of(b["bbox"], W) == "full":
            flush()
            out.append(b)
        else:
            buf.append(b)
    flush()
    return out


# ---------- caption helpers ----------
FIG_RE = r"^\s*(?:Fig(?:ure)?\.?\s*|F\s?I\s?G\s?U\s?R\s?E\s?)(\d+)"
TAB_RE = r"^\s*(?:Table\s*|T\s?A\s?B\s?L\s?E\s?)(\d+)"


def is_caption(t):
    return re.match(FIG_RE, t) or re.match(TAB_RE, t)


def boilerplate_lines(doc):
    c = Counter()
    for pg in doc:
        h = pg.rect.height
        for b in pg.get_text("dict")["blocks"]:
            if "lines" not in b:
                continue
            y0, y1 = b["bbox"][1], b["bbox"][3]
            if y0 < 64 or y1 > h - 56:
                t = block_text(b)
                if 0 < len(t) < 95:
                    c[re.sub(r"\d+", "#", t)] += 1
    return {k for k, v in c.items() if v >= 3}


def graphics_rects(pg):
    rects = [d["rect"] for d in pg.get_drawings()]
    for b in pg.get_text("dict")["blocks"]:
        if "lines" not in b:  # image block
            rects.append(fitz.Rect(b["bbox"]))
    return rects


def _topmost_captions(blocks, regex):
    """One caption per number, the topmost occurrence."""
    found = {}
    for b in blocks:
        t = "".join(s["text"] for l in b["lines"] for s in l["spans"])
        m = re.match(regex, t)
        if m:
            n = int(m.group(1))
            if n not in found or b["bbox"][1] < found[n]["bbox"][1]:
                found[n] = b
    return found


def render_figures_tables(pg, W, fig_dir, figmap, tablemap):
    blocks = [b for b in pg.get_text("dict")["blocks"] if "lines" in b]

    # Rotated (landscape) pages are almost always one full-page wide table.
    # Render the whole page upright (get_pixmap honours /Rotate) instead of
    # trying to crop in the transposed coordinate space.
    if pg.rotation:
        nums = sorted(_topmost_captions(blocks, TAB_RE).keys())
        if nums:
            pix = pg.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE))
            for n in nums:
                pix.save(os.path.join(fig_dir, f"table{n}.png"))
                tablemap[n] = f"table{n}.png"
        return

    grx = graphics_rects(pg)
    W = pg.rect.width            # per-page width
    H = pg.rect.height

    # FIGURE: caption below the graphic
    for n, b in _topmost_captions(blocks, FIG_RE).items():
        col = col_of(b["bbox"], W)
        xr = xrange_of(col, W)
        cy0, cy1 = b["bbox"][1], b["bbox"][3]
        cand = [r for r in grx
                if xr[0] - 2 <= (r.x0 + r.x1) / 2 <= xr[1] + 2
                and r.y1 <= cy0 + 3 and r.y0 >= CONTENT_TOP - 2]
        top = cy0
        used = []
        changed = True
        while changed:
            changed = False
            for r in cand:
                if r.y0 < top and r.y1 >= top - 46:
                    top = min(top, r.y0)
                    if r not in used:
                        used.append(r)
                    changed = True
        if used:
            fx0 = min(min(r.x0 for r in used), b["bbox"][0])
            fx1 = max(max(r.x1 for r in used), b["bbox"][2])
        else:                                   # no graphics found; fall back
            top, fx0, fx1 = max(CONTENT_TOP, cy0 - 320), xr[0], xr[1]
        clip = fitz.Rect(max(28, fx0 - 6), max(CONTENT_TOP, top - 4),
                         min(W - 26, fx1 + 6), cy1 + 3)
        pg.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE), clip=clip).save(
            os.path.join(fig_dir, f"fig{n}.png"))
        figmap[n] = f"fig{n}.png"

    # TABLE: caption above the body. Numeric tables are rendered full-width
    # (cell blocks are scattered, so width inference is unreliable); we just
    # find the vertical extent down to the first large gap.
    for n, b in _topmost_captions(blocks, TAB_RE).items():
        cy0, cy1 = b["bbox"][1], b["bbox"][3]
        below = sorted([bb for bb in blocks if bb["bbox"][1] >= cy1 - 1],
                       key=lambda bb: bb["bbox"][1])
        bottom = cy1
        for bb in below:
            if bb["bbox"][1] - bottom > 28:     # big gap => table ended
                break
            bottom = max(bottom, bb["bbox"][3])
        for r in grx:                            # extend over table rules
            if r.y0 >= cy1 - 2 and r.y1 <= bottom + 28:
                bottom = max(bottom, r.y1)
        clip = fitz.Rect(28, cy0 - 4, W - 26, min(H - 28, bottom + 4))
        pg.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE), clip=clip).save(
            os.path.join(fig_dir, f"table{n}.png"))
        tablemap[n] = f"table{n}.png"


# ---------- inline placement ----------
def refs_in(text, label):
    nums = set()
    pat = r"%s[s]?\.?\s*((?:\d+\s*(?:to|through|[-,]|and)\s*)*\d+)" % label
    for m in re.finditer(pat, text):
        seg = m.group(1)
        for r in re.finditer(r"(\d+)\s*(?:to|through|-)\s*(\d+)", seg):
            nums.update(range(int(r.group(1)), int(r.group(2)) + 1))
        for x in re.findall(r"\d+", seg):
            nums.add(int(x))
    return nums


def place(items, mp, kind, labels):
    placed, out = set(), []
    for it in items:
        out.append(it)
        if it.get("type") == "p":
            hit = set()
            for lab in labels:
                hit |= refs_in(it["text"], lab)
            for n in sorted(hit):
                if n in mp and n not in placed:
                    out.append({"type": kind, "num": n, "src": mp[n]})
                    placed.add(n)
    for n in sorted(mp):
        if n in placed:
            continue
        ins = {"type": kind, "num": n, "src": mp[n]}
        pos = next((i for i, it in enumerate(out)
                    if it.get("type") == kind and it.get("num") == n - 1), None)
        out.insert(pos + 1, ins) if pos is not None else out.append(ins)
        placed.add(n)
    return out


STRONG_MATH = "=<>≤≥≠∑∫∞√∂−·⋅×±∼"


def is_eq(t):
    """Heuristic: is this text block a display equation?"""
    t = t.strip()
    if len(t) > 240:
        return False
    strong = sum(t.count(c) for c in STRONG_MATH)
    if re.search(r"\(\d{1,2}(\.\d{1,2})?\)\s*$", t) and ("=" in t or strong >= 2):
        return True
    sym = sum(t.count(c) for c in STRONG_MATH + "()[]{}|∕")
    lett = sum(c.isalpha() for c in t)
    return strong >= 2 and sym >= 4 and sym > lett * 0.45 and len(t) < 150


def detect_eq_bands(blocks):
    """Group display-equation blocks (and their split fragments) into y-bands."""
    seeds = sorted([b for b in blocks if is_eq(block_text(b))],
                   key=lambda b: b["bbox"][1])
    bands = []
    for b in seeds:
        y0, y1 = b["bbox"][1], b["bbox"][3]
        if bands and y0 - bands[-1]["y1"] < 22:
            bands[-1]["y1"] = max(bands[-1]["y1"], y1)
            bands[-1]["y0"] = min(bands[-1]["y0"], y0)
        else:
            bands.append({"y0": y0, "y1": y1})
    for band in bands:
        members = [bb for bb in blocks
                   if bb["bbox"][3] > band["y0"] - 16 and bb["bbox"][1] < band["y1"] + 16
                   and (is_eq(block_text(bb)) or len(block_text(bb)) < 12)]
        if not members:
            continue
        band["x0"] = min(bb["bbox"][0] for bb in members)
        band["x1"] = max(bb["bbox"][2] for bb in members)
        band["y0"] = min(bb["bbox"][1] for bb in members)
        band["y1"] = max(bb["bbox"][3] for bb in members)
        band["ids"] = {id(bb) for bb in members}
    return [b for b in bands if "ids" in b]


def clean_fragments(items):
    """Drop stray equation fragments (lone subscripts, parens, numbers) and
    re-stitch sentences that those fragments split apart."""
    has_word = re.compile(r"[A-Za-z]{3,}")
    kept = []
    for it in items:
        if it["type"] == "p":
            t = it["text"].strip()
            # a real paragraph has at least two words >=3 letters
            if len(has_word.findall(t)) < 2 and len(t) < 24:
                continue
        kept.append(it)

    merged = []
    for it in kept:
        if (it["type"] == "p" and merged and merged[-1]["type"] == "p"):
            prev = merged[-1]["text"]
            cur = it["text"]
            if not re.search(r"[.?!:)\]]['\"’]?\s*$", prev) and re.match(r"^[a-z(\[]", cur):
                merged[-1]["text"] = prev.rstrip() + " " + cur
                continue
        merged.append(dict(it))
    return merged


def looks_abstract(t):
    head = re.sub(r"\s+", "", t)[:12].lower()
    return head.startswith("abstract") or head.startswith("summary")


def looks_keywords(t):
    return bool(re.match(r"^\s*(Key\s?words|K\s?E\s?Y\s?W\s?O\s?R\s?D\s?S)", t, re.I))


def is_junk(t):
    return bool(
        re.search(r"www\.", t)
        or re.match(r"^\(.*\d{4};\s*\d+", t)
        or re.search(r"\bVolume\s+\d+,\s+Number\s+\d+", t)
        or re.match(r"^\d{1,4}$", t)
        or "Downloaded from" in t
        or "Creative Commons" in t
        or "wileyonlinelibrary.com/journal" in t
        or re.match(r"^https?://", t.strip().lower())
    )


def split_leading_heading(t):
    """Split a block like 'SECTION TITLE Body text starts here...'."""
    m = re.match(r"^([A-Z][A-Z0-9\-]+(?: [A-Z0-9][A-Z0-9\-]+){1,8})\s+([A-Z][a-z].+)$", t)
    if m and 8 <= len(m.group(1)) <= 72:
        return m.group(1), m.group(2)
    return None, t


def heading_of(t, sz, BODY):
    """Return (level, num, text) if the line is a heading, else None."""
    if len(t) > 95:
        return None
    m = re.match(r"^(\d+(?:\.\d+)*)\.?\s+(.+)$", t)
    if m and re.search(r"[A-Za-z]", m.group(2)):
        return ("h2" if "." not in m.group(1) else "h3", m.group(1), m.group(2))
    letters = [c for c in t if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.85 and len(t) >= 4:
        return ("h2", "", t.title())
    if sz > BODY + 1.2:
        return ("h2", "", t)
    return None


# ---------- main ----------
def main(pdf_path, slug, title, authors, venue, year, link_only):
    os.makedirs(PAPERS_DIR, exist_ok=True)
    os.makedirs(PDF_DIR, exist_ok=True)
    shutil.copyfile(pdf_path, os.path.join(PDF_DIR, f"{slug}.pdf"))

    if link_only:
        paper = {
            "slug": slug, "kind": "pdf",
            "title": title or re.sub(r"[_-]+", " ", slugify(pdf_path)).title(),
            "authors": authors or "", "venue": venue, "year": year,
            "pdf": f"{slug}.pdf", "items": [],
        }
        json.dump(paper, open(os.path.join(PAPERS_DIR, f"{slug}.json"), "w"),
                  ensure_ascii=False, indent=1)
        rebuild_index()
        print(f"[{slug}] link-only registered.")
        return

    fig_dir = os.path.join(ROOT, "public", "figures", slug)
    os.makedirs(fig_dir, exist_ok=True)
    d = fitz.open(pdf_path)
    W = d[0].rect.width
    boiler = boilerplate_lines(d)
    hist = Counter()
    for pg in d:
        for b in pg.get_text("dict")["blocks"]:
            if "lines" in b:
                for l in b["lines"]:
                    for s in l["spans"]:
                        hist[round(s["size"])] += len(s["text"])
    BODY = hist.most_common(1)[0][0]

    figmap, tablemap = {}, {}
    for pg in d:
        render_figures_tables(pg, W, fig_dir, figmap, tablemap)

    items = []
    if title:
        items.append({"type": "title", "text": title})
    if authors:
        items.append({"type": "authors", "text": authors})

    seen_abstract = False
    want_abstract = False
    dropcap = None
    eqcount = 0
    for i, pg in enumerate(d):
        if pg.rotation:          # rotated table page -> rendered as image, no prose
            continue
        blocks = [b for b in pg.get_text("dict")["blocks"] if "lines" in b]
        Wp = pg.rect.width

        # display equations -> render the region as an image, drop the garbled text
        eq_bands = detect_eq_bands(blocks)
        for band in eq_bands:
            eqcount += 1
            band["n"] = eqcount
            clip = fitz.Rect(max(28, band["x0"] - 8), band["y0"] - 6,
                             min(Wp - 26, band["x1"] + 8), band["y1"] + 6)
            pg.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE), clip=clip).save(
                os.path.join(fig_dir, f"eq{eqcount}.png"))
        eq_ids = {bid: band for band in eq_bands for bid in band["ids"]}
        eq_done = set()

        for b in reading_order(blocks, W):
            if id(b) in eq_ids:                    # part of a display equation
                band = eq_ids[id(b)]
                if band["n"] not in eq_done:
                    items.append({"type": "equation", "src": f"eq{band['n']}.png"})
                    eq_done.add(band["n"])
                continue
            sz, t = maxsize(b), block_text(b)
            if not t or is_caption(t) or is_junk(t):
                continue
            if re.sub(r"\d+", "#", t) in boiler:
                continue

            # abstract marker, possibly followed by its body in the next block
            if looks_abstract(t):
                rest = re.sub(r"^\s*(Abstract|S\s?U\s?M\s?M\s?A\s?R\s?Y|Summary)[:\.\s]*", "", t, flags=re.I).strip()
                if len(rest) >= 40:
                    items.append({"type": "abstract", "text": rest})
                else:
                    want_abstract = True
                seen_abstract = True
                continue
            if want_abstract and abs(sz - BODY) < 2 and len(t) >= 40 \
                    and not re.match(r"^\d+(\.\d+)*\.?\s", t):
                items.append({"type": "abstract", "text": t})
                want_abstract = False
                continue
            if looks_keywords(t):
                rest = re.sub(r"^\s*(Key\s?words|K\s?E\s?Y\s?W\s?O\s?R\s?D\s?S)[:\.\s]*", "", t, flags=re.I).strip()
                if rest:
                    items.append({"type": "keywords", "text": rest})
                seen_abstract = True
                continue

            # page-0 header (title/authors/affiliations) before the abstract -> skip
            if i == 0 and not seen_abstract:
                continue

            # drop-cap: a lone big initial letter -> prepend to next paragraph
            if len(t) <= 2 and sz > BODY + 5:
                dropcap = t
                continue
            if dropcap and abs(sz - BODY) < 1.6:
                t = dropcap + t.lstrip()
                dropcap = None

            if sz < BODY - 1.3:          # footnotes / affiliations / tiny
                continue

            # a heading glued to the start of a paragraph -> split it off
            hp, t = split_leading_heading(t)
            if hp:
                items.append({"type": "h2", "num": "", "text": hp.title()})

            h = heading_of(t, sz, BODY)
            if h:
                items.append({"type": h[0], "num": h[1], "text": h[2]})
            else:
                items.append({"type": "p", "text": t})

    items = clean_fragments(items)
    items = place(items, figmap, "figure", ["Figure", "Fig"])
    items = place(items, tablemap, "table", ["Table"])

    def first(tp):
        return next((it["text"] for it in items if it.get("type") == tp), "")

    paper = {
        "slug": slug, "kind": "paper",
        "title": title or first("title"),
        "authors": authors or first("authors"),
        "venue": venue, "year": year,
        "abstract": first("abstract"),
        "pdf": f"{slug}.pdf",
        "items": items,
    }
    json.dump(paper, open(os.path.join(PAPERS_DIR, f"{slug}.json"), "w"),
              ensure_ascii=False, indent=1)
    rebuild_index()
    print(f"[{slug}] figs={sorted(figmap)} tables={sorted(tablemap)} items={len(items)}")


def rebuild_index():
    files = sorted(f[:-5] for f in os.listdir(PAPERS_DIR) if f.endswith(".json"))
    lines = ["// AUTO-GENERATED by scripts/extract.py — lists every paper JSON.",
             "// You can also edit by hand: add an import and include it in `papersData`.",
             ""]
    var = {}
    for s in files:
        v = re.sub(r"_(\w)", lambda m: m.group(1).upper(),
                   "_" + re.sub(r"[^a-zA-Z0-9]", "_", s))
        var[s] = v
        lines.append(f'import {v} from "./papers/{s}.json";')
    lines += ["", "export const papersData = [" + ", ".join(var[s] for s in files) + "];", ""]
    open(INDEX_TS, "w").write("\n".join(lines))


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit('usage: python scripts/extract.py <pdf> <slug> [--title ..] [--authors ..] [--venue ..] [--year N] [--link-only]')
    pdf = args[0]
    title = authors = venue = None
    year = None
    link_only = False
    slug = None
    i = 1
    while i < len(args):
        a = args[i]
        if a == "--title":
            title = args[i + 1]; i += 2
        elif a == "--authors":
            authors = args[i + 1]; i += 2
        elif a == "--venue":
            venue = args[i + 1]; i += 2
        elif a == "--year":
            year = int(args[i + 1]); i += 2
        elif a == "--link-only":
            link_only = True; i += 1
        else:
            slug = a; i += 1
    slug = slug or slugify(pdf)
    main(pdf, slug, title, authors, venue, year, link_only)
