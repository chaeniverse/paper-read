#!/usr/bin/env python3
"""Convert a Marker output folder into data/papers/<slug>.json.

Marker (https://github.com/datalab-to/marker) converts a PDF into:
    marker_out/<stem>/<stem>.md        markdown with LaTeX math ($...$, $$...$$)
    marker_out/<stem>/*.jpeg|*.png     extracted figure/picture images
    marker_out/<stem>/<stem>_meta.json

This yields selectable text + clean KaTeX equations AND real figure images,
replacing the PNG-image equations from scripts/extract.py. Figures are placed
inline by Marker already (reading order); extracted images are copied into
public/figures/<slug>/.

Usage:
    python3 scripts/marker_to_json.py marker_out/<stem> <slug> \
        [--title ..] [--authors ..] [--venue ..] [--year N]
Metadata defaults to the existing data/papers/<slug>.json, overridden by flags.
"""
import sys, os, re, json, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPERS_DIR = os.path.join(ROOT, "data", "papers")
FIG_ROOT = os.path.join(ROOT, "public", "figures")
INDEX_TS = os.path.join(ROOT, "data", "papers.index.ts")
IMG_EXT = (".jpeg", ".jpg", ".png", ".webp")


# ---------- inline markup cleanup (math-safe) ----------
MATH_SPAN = re.compile(r"\$\$[\s\S]*?\$\$|\$[^$\n]*?\$")


def strip_md(text):
    """Remove markdown/HTML emphasis everywhere EXCEPT inside $...$ math."""
    out, last = [], 0
    for m in MATH_SPAN.finditer(text):
        out.append(_emph(text[last:m.start()]))
        out.append(m.group(0))
        last = m.end()
    out.append(_emph(text[last:]))
    return "".join(out)


def _emph(s):
    s = re.sub(r"<span[^>]*>|</span>", "", s)               # marker anchors
    s = re.sub(r"</?su[bp]>", "", s)                         # <sup>/<sub> -> keep text
    s = s.replace("<br>", " ").replace("<br/>", " ")
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)                 # **bold**
    s = re.sub(r"(?<!\w)\*([^*\n]+)\*(?!\w)", r"\1", s)      # *italic*
    s = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"\1", s)        # _italic_
    # leftover stray italic around short OCR tokens (e.g. *x*2 -> x2)
    s = re.sub(r"\*([^*\s]{1,8})\*", r"\1", s)
    return s


# ---------- tables ----------
def md_table_to_html(rows):
    cells = []
    for r in rows:
        r = r.strip().strip("|")
        cells.append([c.strip() for c in r.split("|")])
    body = [c for c in cells if not all(re.fullmatch(r":?-{2,}:?", (x or "-").strip()) for x in c)]
    # drop trailing all-empty columns (Marker often leaves a dangling '| |')
    while body and all(len(r) and r[-1] == "" for r in body):
        body = [r[:-1] for r in body]
    if not body:
        return ""
    head, *rest = body
    html = ["<table><thead><tr>"] + [f"<th>{c}</th>" for c in head] + ["</tr></thead><tbody>"]
    for row in rest:
        html.append("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
    html.append("</tbody></table>")
    return "".join(html)


# ---------- headings ----------
def heading_of(text):
    m = re.match(r"^(#{1,6})\s+(.*)$", text)
    if not m:
        return None
    body = m.group(2).strip().rstrip("#").strip()
    body = re.sub(r"^\|\s*", "", body).strip()              # stray leading pipe
    if not body:
        return None
    nm = re.match(r"^(\d+(?:\.\d+)*)\s*[.|]?\s+(.+)$", body)
    if nm:
        num, txt = nm.group(1), re.sub(r"^\|\s*", "", nm.group(2)).strip()
        return {"type": ("h3" if "." in num else "h2"), "num": num, "text": txt}
    # marker heading levels track font size, not structure -> shallow = h2
    return {"type": ("h2" if len(m.group(1)) <= 3 else "h3"), "num": "", "text": body}


# ---------- markdown -> items ----------
def parse_md(text, img_names):
    text = re.sub(r"<!--[\s\S]*?-->", "", text.replace("\r\n", "\n"))
    lines = text.split("\n")
    items, buf = [], []
    i, n = 0, len(lines)

    def flush():
        if not buf:
            return
        para = re.sub(r"\s+", " ", strip_md(" ".join(x.strip() for x in buf))).strip()
        buf.clear()
        if not para:
            return
        h = heading_of(para)
        if h:
            items.append(h)
        elif re.fullmatch(r"\$\$[\s\S]+\$\$", para):
            items.append({"type": "math", "tex": para.strip("$").strip()})
        else:
            items.append({"type": "p", "text": para})

    while i < n:
        raw = lines[i]
        s = raw.strip()

        if s.lower().startswith("<table"):                  # HTML table block
            flush()
            chunk = raw
            while "</table>" not in chunk.lower() and i + 1 < n:
                i += 1; chunk += "\n" + lines[i]
            items.append({"type": "table-html", "html": _emph(chunk).strip()})
            i += 1; continue

        if s.startswith("|") and i + 1 < n and \
                re.match(r"^\s*\|?[\s:|-]*-{2,}[\s:|-]*\|?\s*$", lines[i + 1]):
            flush()
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(lines[i]); i += 1
            html = md_table_to_html(rows)
            if html:
                items.append({"type": "table-html", "html": html})
            continue

        if s.startswith("$$"):                              # display math
            flush()
            chunk = s
            while chunk.count("$$") < 2 and i + 1 < n:
                i += 1; chunk += "\n" + lines[i].strip()
            inner = re.sub(r"^\$\$|\$\$$", "", chunk.strip()).strip()
            if inner:
                items.append({"type": "math", "tex": inner})
            i += 1; continue

        m = re.match(r"^!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)\s*$", s)
        if m:                                               # standalone image
            flush()
            src = os.path.basename(m.group("src"))
            kind = "table" if re.search(r"table", m.group("alt"), re.I) else "figure"
            if src in img_names:
                items.append({"type": kind, "num": _num(m.group("alt")), "src": src})
            i += 1; continue

        if s == "":
            flush(); i += 1; continue
        buf.append(raw); i += 1

    flush()
    return items


def _num(alt):
    m = re.search(r"(\d+)", alt or "")
    return int(m.group(1)) if m else 0


# ---------- front-matter + post processing ----------
def restructure(items):
    # attach equation numbers: a lone "(2.1)" paragraph right after a math block
    merged = []
    for it in items:
        if it["type"] == "p" and merged and merged[-1]["type"] == "math" \
                and "num" not in merged[-1]:
            m = re.fullmatch(r"\(?(\d+(?:\.\d+)*)\)?", it["text"].strip())
            if m:
                merged[-1]["num"] = m.group(1); continue
        merged.append(it)
    items = merged

    # find the abstract + keywords anywhere in the front region (~first 15 items)
    abstract, keywords, abs_idx = "", "", None
    for i, it in enumerate(items[:15]):
        t = it.get("text", "")
        if it["type"] in ("h2", "h3") and re.fullmatch(r"(?i)(abstract|summary)\s*", t):
            for j in range(i + 1, len(items)):
                if items[j]["type"] == "p" and len(items[j]["text"]) > 40:
                    abstract, abs_idx = items[j]["text"], j; break
        elif it["type"] in ("h2", "h3") and re.fullmatch(r"(?i)key\s?words?\s*", t):
            for j in range(i + 1, len(items)):
                if items[j]["type"] == "p":
                    keywords = items[j]["text"]; break
        elif it["type"] == "p":
            mk = re.match(r"(?i)^key\s?words?\s*[:.\s]\s*(.+)", t)
            if mk:
                keywords = mk.group(1)
            ma = re.match(r"(?i)^(abstract|summary)\s*[:.\s]\s*(.{40,})", t)
            if ma and not abstract:
                abstract, abs_idx = ma.group(2), i

    # content start: first numbered section, else just after the abstract para.
    cstart = next((i for i, it in enumerate(items)
                   if it["type"] in ("h2", "h3") and it.get("num")), None)
    if cstart is None:
        cstart = (abs_idx + 1) if abs_idx is not None else 0
    body = items[cstart:]

    # strip leftover journal/front-matter junk paragraphs from the body
    JUNK = re.compile(r"(?i)^(submitted |accepted |received |posted |correspondence:|"
                      r"doi:?\s|issn|copyright|©|c the author|\(epidemiology|"
                      r"supplemental digital|published by|downloaded from|"
                      r"wileyonlinelibrary|reprints:|e-?mail:|https?://)")
    HEADER = re.compile(r"(?i)(volume\s+\d+,?\s+number\s+\d+|^\w[\w .]{0,30}[•·]\s*volume)")
    body = [it for it in body if not (it["type"] == "p"
            and (JUNK.match(it["text"]) or
                 (len(it["text"]) < 80 and HEADER.search(it["text"]))))]

    result = []
    if abstract:
        result.append({"type": "abstract", "text": abstract})
    if keywords:
        result.append({"type": "keywords", "text": re.sub(r"\.$", "", keywords).strip()})
    result += body
    return result, abstract


# ---------- io ----------
def copy_images(src_dir, slug):
    dst = os.path.join(FIG_ROOT, slug)
    os.makedirs(dst, exist_ok=True)
    # start clean so stale extract.py PNGs (eqN/figN) don't linger
    for f in os.listdir(dst):
        os.remove(os.path.join(dst, f))
    names = set()
    for f in os.listdir(src_dir):
        if f.lower().endswith(IMG_EXT):
            shutil.copyfile(os.path.join(src_dir, f), os.path.join(dst, f))
            names.add(f)
    return names


def main(src_dir, slug, title, authors, venue, year):
    if os.path.isdir(src_dir):
        mds = [f for f in os.listdir(src_dir) if f.endswith(".md")]
        if not mds:
            sys.exit(f"no .md found in {src_dir}")
        md_path = os.path.join(src_dir, mds[0])
    else:
        md_path, src_dir = src_dir, os.path.dirname(src_dir)

    existing = {}
    jp = os.path.join(PAPERS_DIR, f"{slug}.json")
    if os.path.exists(jp):
        existing = json.load(open(jp))

    img_names = copy_images(src_dir, slug)
    items = parse_md(open(md_path, encoding="utf-8").read(), img_names)
    items, abstract = restructure(items)

    paper = {
        "slug": slug, "kind": "paper",
        "title": title or existing.get("title") or slug,
        "authors": authors or existing.get("authors", ""),
        "venue": venue or existing.get("venue"),
        "year": year or existing.get("year"),
        "abstract": abstract or existing.get("abstract", ""),
        "pdf": existing.get("pdf", f"{slug}.pdf"),
        "items": items,
    }
    json.dump(paper, open(jp, "w"), ensure_ascii=False, indent=1)
    rebuild_index()
    from collections import Counter
    print(f"[{slug}] {dict(Counter(it['type'] for it in items))}  images={len(img_names)}")


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
    if len(args) < 2:
        sys.exit("usage: python3 scripts/marker_to_json.py <marker_out/stem dir> <slug> "
                 "[--title ..] [--authors ..] [--venue ..] [--year N]")
    src, slug = args[0], args[1]
    title = authors = venue = None
    year = None
    i = 2
    while i < len(args):
        a = args[i]
        if a == "--title": title = args[i + 1]; i += 2
        elif a == "--authors": authors = args[i + 1]; i += 2
        elif a == "--venue": venue = args[i + 1]; i += 2
        elif a == "--year": year = int(args[i + 1]); i += 2
        else: i += 1
    main(src, slug, title, authors, venue, year)
