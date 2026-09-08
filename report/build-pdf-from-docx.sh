#!/usr/bin/env bash
set -euo pipefail

# Synchronize the report representations, render the PDF from the current Word
# file, then record source and artifact hashes for the harness audit.
#
# Requires pandoc and a PDF engine (e.g. tectonic). Until those are installed in
# your fork, this script will report the missing tool and stop; keep report.md
# and report.tex synchronized by hand in the meantime.
cd "$(dirname "$0")"

command -v pandoc >/dev/null 2>&1 || { echo "pandoc not found; install it to build the report" >&2; exit 1; }

pandoc report.md -o report.docx
pandoc report.docx --pdf-engine=tectonic --output=report.pdf

# Hash the working sources. Figures are included only once they exist.
figs=(figures/*.png)
if [[ -e "${figs[0]}" ]]; then
  sha256sum report.md report.tex sections/*.tex figures.py figures/*.png > source.sha256
else
  sha256sum report.md report.tex sections/*.tex figures.py > source.sha256
fi
sha256sum report.docx report.pdf > parity.sha256
echo "report build complete; source.sha256 and parity.sha256 refreshed"
