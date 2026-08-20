#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
pdfinfo main.pdf | sed -n 's/^Pages:\s*//p' | awk '{print "pages="$1}'
