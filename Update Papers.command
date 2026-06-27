#!/usr/bin/env bash
# Double-click this file (in Finder) to import any new PDFs from sources/
# into the app. It runs scripts/build_papers.py for you.
#
# Equivalent terminal command:  python3 scripts/build_papers.py
cd "$(dirname "$0")" || exit 1

echo "📄  Paper-Read — importing new PDFs from sources/ ..."
echo

python3 scripts/build_papers.py "$@"
status=$?

echo
if [ $status -eq 0 ]; then
  echo "✅  Done. Run 'npm run dev' to preview, then commit & push to deploy."
else
  echo "⚠️  Finished with errors (see above)."
fi
echo
echo "Press Return to close…"
read -r _
