#!/usr/bin/env python3
"""Convert PDF(s) to Markdown+LaTeX with the Mathpix Convert API.

Mathpix has the best math/LaTeX OCR accuracy. This submits each PDF, polls
until done, and downloads the result as Markdown (with $...$ / $$...$$ math)
into mathpix_out/<name>.md (and .mmd).

Credentials come from the environment ONLY (never hard-code / paste in chat):
    export MATHPIX_APP_ID="..."
    export MATHPIX_APP_KEY="..."
Get them at https://console.mathpix.com (Convert API). Billed per page.

Usage:
    python3 scripts/mathpix_convert.py sources/*.pdf
    python3 scripts/mathpix_convert.py            # the 4 original-article PDFs
"""
import os, sys, time, glob, json
import requests

API = "https://api.mathpix.com/v3/pdf"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mathpix_out")

APP_ID = os.environ.get("MATHPIX_APP_ID")
APP_KEY = os.environ.get("MATHPIX_APP_KEY")

# default set = the four original articles (public/pdfs copies)
DEFAULTS = ["public/pdfs/austin-ici.pdf", "public/pdfs/competing-risks-prognostic.pdf",
            "public/pdfs/concordance-competing-risks.pdf", "public/pdfs/internal-validation.pdf"]

OPTIONS = {
    "conversion_formats": {"md": True},
    "math_inline_delimiters": ["$", "$"],
    "math_display_delimiters": ["$$", "$$"],
    "rm_spaces": True,
    "enable_tables_fallback": True,
}


def headers():
    h = {"app_key": APP_KEY}
    if APP_ID:  # older accounts use app_id + app_key; newer keys are app_key-only
        h["app_id"] = APP_ID
    return h


def submit(pdf):
    with open(pdf, "rb") as f:
        r = requests.post(API, headers=headers(),
                          data={"options_json": json.dumps(OPTIONS)},
                          files={"file": f})
    try:
        body = r.json()
    except Exception:
        body = {"_raw": r.text[:300]}
    if "pdf_id" not in body:
        raise RuntimeError(f"HTTP {r.status_code} — no pdf_id. Response: {body}")
    return body["pdf_id"]


def wait(pdf_id, label, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = requests.get(f"{API}/{pdf_id}", headers=headers())
        r.raise_for_status()
        st = r.json()
        status = st.get("status")
        if status == "completed":
            return True
        if status == "error":
            print(f"  ERROR: {st}")
            return False
        pct = st.get("percent_done", 0)
        print(f"  {label}: {status} {pct}% ({st.get('num_pages','?')}p)", flush=True)
        time.sleep(4)
    print("  timeout")
    return False


def download(pdf_id, base):
    for ext in ("md", "mmd"):
        r = requests.get(f"{API}/{pdf_id}.{ext}", headers=headers())
        if r.ok:
            path = os.path.join(OUT, f"{base}.{ext}")
            open(path, "w", encoding="utf-8").write(r.text)
            print(f"  saved {path} ({len(r.text)} chars)")


def main(pdfs):
    if not APP_KEY:
        sys.exit("Set MATHPIX_APP_KEY env var first (and MATHPIX_APP_ID if your "
                 "account uses one). Get keys at https://console.mathpix.com.")
    os.makedirs(OUT, exist_ok=True)
    pdfs = pdfs or DEFAULTS
    for pdf in pdfs:
        if not os.path.isfile(pdf):
            print(f"skip (missing): {pdf}"); continue
        base = os.path.splitext(os.path.basename(pdf))[0]
        print(f"\n→ {pdf}")
        try:
            pid = submit(pdf)
            print(f"  pdf_id={pid}")
            if wait(pid, base):
                download(pid, base)
        except Exception as e:
            print(f"  FAILED: {e}")
    print(f"\nDone. Markdown in {OUT}/  → integrate with scripts/marker_to_json.py "
          "(or I'll adapt it for Mathpix output).")


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if not a.startswith("--")])
