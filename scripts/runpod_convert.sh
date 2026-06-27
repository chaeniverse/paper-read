#!/usr/bin/env bash
# Runs ON a RunPod (or any CUDA Linux box) to batch-convert PDFs with Marker.
#
# Workflow (driven from the Mac):
#   1. rsync public/pdfs/  ->  pod:/workspace/pdfs/
#   2. ssh pod 'bash /workspace/runpod_convert.sh'      # this script
#   3. rsync pod:/workspace/marker_out/  ->  local marker_out/
#
# On the pod it installs marker-pdf once (cached on the volume) and converts
# every PDF in /workspace/pdfs to markdown + extracted images, using the GPU.
set -euo pipefail

WORK="${WORK:-/workspace}"
IN="$WORK/pdfs"
OUT="$WORK/marker_out"
mkdir -p "$OUT"

echo "== GPU =="; nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || echo "no nvidia-smi"

# Install marker into an isolated env once (pip is fine on a fresh pod).
if ! command -v marker >/dev/null 2>&1; then
  echo "== installing marker-pdf =="
  pip install -q --upgrade pip
  pip install -q marker-pdf
fi

echo "== converting $(ls "$IN"/*.pdf 2>/dev/null | wc -l) PDF(s) on GPU =="
# Marker batch mode: point it at the input folder. TORCH_DEVICE=cuda is implicit
# on a GPU box; set explicitly to be safe.
TORCH_DEVICE=cuda marker "$IN" \
  --output_dir "$OUT" \
  --output_format markdown \
  --workers "${WORKERS:-4}"

echo "== done. results in $OUT =="
find "$OUT" -name '*.md' | sed "s#$OUT/##"
