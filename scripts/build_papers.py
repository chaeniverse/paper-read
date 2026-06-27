#!/usr/bin/env python3
"""One-shot pipeline: drop a PDF in sources/ -> it shows up in the app.

For every PDF in sources/ the app does not already have, this:
    1. copies it to public/pdfs/<slug>.pdf
    2. runs Marker (OCR) -> marker_out/<slug>/<slug>.md + extracted images
    3. runs marker_to_json -> data/papers/<slug>.json (text + KaTeX math + figures)

"Already in the app" is detected by content hash against public/pdfs/*.pdf, so
re-running is safe. Use --force to reprocess.

NOTE: Marker on a Mac (MPS) is slow (~minutes/page). For more than a paper or
two, convert on a GPU instead and only run marker_to_json locally:
    • RunPod:  scripts/runpod_convert.sh  (see README)
    • Colab:   Marker_Colab.ipynb         (free T4 GPU)

Usage:
    python3 scripts/build_papers.py                 # new PDFs in sources/
    python3 scripts/build_papers.py --force          # reprocess all in public/pdfs
    python3 scripts/build_papers.py sources/x.pdf    # specific files
"""
import os, re, sys, glob, shutil, hashlib, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(ROOT, "sources")
PDF_DIR = os.path.join(ROOT, "public", "pdfs")
MARKER_OUT = os.path.join(ROOT, "marker_out")
PY = sys.executable or "python3"


def info(m): print(f"\033[1;36m▶ {m}\033[0m", flush=True)
def ok(m): print(f"  \033[32m✓\033[0m {m}", flush=True)
def warn(m): print(f"  \033[33m!\033[0m {m}", flush=True)


def slugify(path):
    s = re.sub(r"\.pdf$", "", os.path.basename(path), flags=re.I)
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return re.sub(r"-+", "-", s)[:60] or "paper"


def sha(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def known_by_hash():
    return {sha(p): os.path.splitext(os.path.basename(p))[0]
            for p in glob.glob(os.path.join(PDF_DIR, "*.pdf"))}


def find_marker():
    cand = os.path.expanduser("~/.local/bin/marker_single")
    return cand if os.path.exists(cand) else shutil.which("marker_single")


def process(pdf, slug, marker_bin):
    info(f"{os.path.basename(pdf)}  →  slug '{slug}'")
    os.makedirs(PDF_DIR, exist_ok=True)
    dst = os.path.join(PDF_DIR, f"{slug}.pdf")
    if os.path.abspath(pdf) != os.path.abspath(dst):
        shutil.copyfile(pdf, dst)

    os.makedirs(MARKER_OUT, exist_ok=True)
    env = dict(os.environ, TORCH_DEVICE=os.environ.get("TORCH_DEVICE", "mps"))
    r = subprocess.run([marker_bin, dst, "--output_dir", MARKER_OUT,
                        "--output_format", "markdown"], cwd=ROOT, env=env)
    out_dir = os.path.join(MARKER_OUT, slug)
    if r.returncode != 0 or not os.path.isdir(out_dir):
        warn("marker failed; skipping"); return False
    ok("OCR done (markdown + images)")

    if subprocess.run([PY, os.path.join("scripts", "marker_to_json.py"),
                       out_dir, slug], cwd=ROOT).returncode != 0:
        warn("marker_to_json failed"); return False
    ok("integrated into data/papers + figures")
    return True


def main(argv):
    force = "--force" in argv
    explicit = [a for a in argv if not a.startswith("--")]

    marker_bin = find_marker()
    if not marker_bin:
        sys.exit("marker not installed locally. Install: uv tool install marker-pdf "
                 "--python 3.12   (or use RunPod / Marker_Colab.ipynb for GPU)")

    known = known_by_hash()
    if explicit:
        jobs = [(p, known.get(sha(p)) or slugify(p)) for p in explicit]
    elif force:
        jobs = [(os.path.join(PDF_DIR, f"{s}.pdf"), s) for s in known.values()]
    else:
        jobs = []
        for pdf in sorted(glob.glob(os.path.join(SOURCES, "*.pdf"))):
            h = sha(pdf)
            if h in known:
                ok(f"already in app: {os.path.basename(pdf)} ({known[h]})")
            else:
                jobs.append((pdf, slugify(pdf)))

    if not jobs:
        print("\nNothing to do. ✨  (drop PDFs in sources/, or use --force)"); return

    print(f"\nProcessing {len(jobs)} PDF(s) with Marker (slow on Mac MPS)…")
    done = sum(process(p, s, marker_bin) for p, s in jobs)
    info("Done")
    print(f"  {done}/{len(jobs)} processed.")
    print("  Preview:  npm run dev   →   http://localhost:3000")
    print("  Deploy:   git add -A && git commit -m 'add papers' && git push")


if __name__ == "__main__":
    main(sys.argv[1:])
