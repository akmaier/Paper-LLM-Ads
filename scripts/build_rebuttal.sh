#!/bin/zsh
# Build the single rebuttal submission PDF:
#   page 1..n   = reviewer response (response.pdf, <=3 pp)
#   then        = change-marked manuscript (main_highlighted.pdf, \rev{} in blue)
#   then        = clean manuscript (main_clean.pdf)
# Concatenated with pdfunite -> paper/rebuttal_submission.pdf
set -e
export PATH="/Library/TeX/texbin:$PATH"
cd /Users/maier/Documents/code/Paper-LLM-Ads/paper

echo "[1/4] clean manuscript"
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/tmp/r_clean1.log 2>&1
bibtex main >/tmp/r_bib.log 2>&1 || true
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/tmp/r_clean2.log 2>&1
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/tmp/r_clean3.log 2>&1
cp main.pdf main_clean.pdf

echo "[2/4] change-marked manuscript (\\def\\HLON{})"
pdflatex -interaction=nonstopmode -halt-on-error "\def\HLON{}\input{main.tex}" >/tmp/r_hl1.log 2>&1
bibtex main >/tmp/r_hlbib.log 2>&1 || true
pdflatex -interaction=nonstopmode -halt-on-error "\def\HLON{}\input{main.tex}" >/tmp/r_hl2.log 2>&1
pdflatex -interaction=nonstopmode -halt-on-error "\def\HLON{}\input{main.tex}" >/tmp/r_hl3.log 2>&1
cp main.pdf main_highlighted.pdf

echo "[3/4] reviewer response"
pdflatex -interaction=nonstopmode -halt-on-error response.tex >/tmp/r_resp1.log 2>&1
pdflatex -interaction=nonstopmode -halt-on-error response.tex >/tmp/r_resp2.log 2>&1

# rebuild clean main.pdf as the canonical artifact (last \HLON build left main.pdf highlighted)
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/tmp/r_final.log 2>&1

echo "[4/4] concatenate"
pdfunite response.pdf main_highlighted.pdf main_clean.pdf rebuttal_submission.pdf

echo "=== page counts ==="
for f in response main_highlighted main_clean rebuttal_submission; do
  printf "%-22s " "$f.pdf"; pdfinfo $f.pdf 2>/dev/null | grep Pages
done
