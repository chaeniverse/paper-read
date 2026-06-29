#!/usr/bin/env python3
"""Convert a Mathpix `.md` file into data/papers/<slug>.json.

Mathpix Convert gives the cleanest math (proper $...$ / $$...$$ LaTeX). Format is
close to Marker's markdown, so we reuse marker_to_json's helpers; the differences
handled here:
  * figure images are remote Mathpix CDN URLs -> downloaded to public/figures/<slug>/
    (they can expire, so we make a permanent local copy)
  * footnote markers ([^N]) / definitions are stripped

Usage:
    python3 scripts/mathpix_to_json.py mathpix_out/<slug>.md <slug> [--title ..] ...
"""
import sys, os, re, json
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import marker_to_json as M  # reuse strip_md/heading_of/md_table_to_html/restructure/...

FIG_ROOT = M.FIG_ROOT
PAPERS_DIR = M.PAPERS_DIR


def parse_md(text, slug):
    text = re.sub(r"<!--[\s\S]*?-->", "", text.replace("\r\n", "\n"))
    text = re.sub(r"^\[\^\d+\]:.*$", "", text, flags=re.M)   # footnote definitions
    dst = os.path.join(FIG_ROOT, slug)
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(dst):                                 # start clean
        os.remove(os.path.join(dst, f))

    lines = text.split("\n")
    items, buf = [], []
    img_i = [0]
    i, n = 0, len(lines)

    def dl_image(url):
        img_i[0] += 1
        name = f"mpx{img_i[0]}.jpg"
        try:
            r = requests.get(url, timeout=60)
            if r.ok and r.content:
                open(os.path.join(dst, name), "wb").write(r.content)
                return name
        except Exception as e:
            print(f"  ! image download failed: {e}")
        return None

    def flush():
        if not buf:
            return
        para = re.sub(r"\s+", " ", M.strip_md(" ".join(x.strip() for x in buf))).strip()
        para = re.sub(r"\[\^\d+\]", "", para)                 # footnote markers
        buf.clear()
        if not para:
            return
        h = M.heading_of(para)
        if h:
            items.append(h)
        elif re.fullmatch(r"\$\$[\s\S]+\$\$", para):
            items.append({"type": "math", "tex": M.clean_tex(para.strip("$"))})
        else:
            items.append({"type": "p", "text": para})

    while i < n:
        raw = lines[i]
        s = raw.strip()

        if s.startswith("|") and i + 1 < n and \
                re.match(r"^\s*\|?[\s:|-]*-{2,}[\s:|-]*\|?\s*$", lines[i + 1]):
            flush()
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(lines[i]); i += 1
            html = M.md_table_to_html(rows)
            if html:
                items.append({"type": "table-html", "html": html})
            continue

        if s.startswith("$$"):
            flush()
            chunk = s
            while chunk.count("$$") < 2 and i + 1 < n:
                i += 1; chunk += "\n" + lines[i].strip()
            inner = M.clean_tex(re.sub(r"^\$\$|\$\$$", "", chunk.strip()))
            if inner:
                items.append({"type": "math", "tex": inner})
            i += 1; continue

        m = re.match(r"^!\[[^\]]*\]\((?P<src>[^)]+)\)\s*$", s)
        if m:
            flush()
            src = m.group("src")
            name = dl_image(src) if src.startswith("http") else os.path.basename(src)
            if name:
                items.append({"type": "figure", "num": img_i[0], "src": name})
            i += 1; continue

        if s == "":
            flush(); i += 1; continue
        buf.append(raw); i += 1

    flush()
    return items


def main(md_path, slug, title, authors, venue, year):
    existing = {}
    jp = os.path.join(PAPERS_DIR, f"{slug}.json")
    if os.path.exists(jp):
        existing = json.load(open(jp))

    items = parse_md(open(md_path, encoding="utf-8").read(), slug)
    items, abstract = M.restructure(items)

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
    M.rebuild_index()
    from collections import Counter
    print(f"[{slug}] {dict(Counter(it['type'] for it in items))}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit("usage: python3 scripts/mathpix_to_json.py <mathpix_out/slug.md> <slug> "
                 "[--title ..] [--authors ..] [--venue ..] [--year N]")
    md, slug = args[0], args[1]
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
    main(md, slug, title, authors, venue, year)
