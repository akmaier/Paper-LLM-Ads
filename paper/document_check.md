# Document Check — TIPS 2026 (ICPR Workshop) submission

This file is the working checklist that must pass before the paper is
considered submission-ready. Items are grouped by *workshop-imposed
constraints* (deadline-critical) and *standard quality checks* (apply to
any LaTeX paper). Re-run the bash commands at the bottom of the file
before each commit.

---

## 1. Workshop constraints — TIPS 2026

Source: <https://tips2026.midasoc.org> (fetched 2026-05-10).

| item | requirement | status |
|---|---|---|
| Workshop | TIPS 2026 — Workshop on Textual Information Processing & Synthesis in the Wild, in conjunction with ICPR 2026 (Lyon, 21 Aug 2026) | — |
| Submission deadline | **2026-05-12, 23:59 AoE** | T-2 days |
| Format | Springer **LNCS** (Lecture Notes in Computer Science) | `\documentclass[runningheads]{llncs}` |
| Page limit | **up to 15 pages including references**; minimum 6 pages for proceedings inclusion | enforce in `make check` |
| Review style | **Single-blind**: authors *must* include names and affiliations | author block visible in title-page |
| Submission portal | <https://cmt3.research.microsoft.com/TIPS2026> | manual upload |
| Topics in scope | NLP, multimodal document understanding, sentiment analysis, generative document analysis methods | our paper sits at NLP × LLM evaluation |
| Notification | 2026-06-12 | — |
| Camera-ready | 2026-06-20 | — |

LNCS-specific gotchas:
- Use `\documentclass[runningheads]{llncs}` (do **not** add `[twocolumn]`; LNCS is single-column).
- Authors as `\author{Name1\inst{1} \and Name2\inst{2}\and ...}` and institute block via `\institute{...}`.
- `\maketitle` produces the title page; do not add custom title formatting.
- Bibliography style: `\bibliographystyle{splncs04}` (the LNCS `.bst` file shipped with `llncs.cls`). References must use the LNCS numerical style, not author-year.
- Figures/tables: caption *below* figures, *above* tables (LNCS convention).
- Acknowledgements section heading: `\section*{Acknowledgements}` (no number).

## 2. Standard LaTeX quality checks

These apply to every paper regardless of venue.

### 2a. Page-limit & layout
- [ ] Compiled PDF page count ≤ 15 (incl. references). Run `make check`.
- [ ] No `Overfull \hbox` or `Underfull \hbox` warnings in the log
  (small `Underfull \vbox` near the end of pages is OK; `Overfull \hbox`
  is not).
- [ ] No content overflowing into the footer / margin.
- [ ] No widows/orphans (single line of paragraph at top/bottom of page) —
  only fixable by `\looseness=-1` or text edit; flag don't crash.
- [ ] All section titles fit on one line (no LNCS warning about title
  too long for runningheads).

### 2b. References & citations
- [ ] **Every `\cite{key}` resolves to a real BibTeX entry** (no
  "?" or "??" in the compiled PDF). Run the grep below.
- [ ] **No hallucinated references**: every BibTeX entry must point to a
  real paper. The bibliography is verified by hand against either:
  - an arXiv ID (resolvable via <https://arxiv.org/abs/XXXX.YYYYY>),
  - a DOI (resolvable via <https://doi.org/...>),
  - or a published-venue URL.
  This file (`references_audit.md`) tracks the verification status of
  each entry.
- [ ] No duplicate citation keys.
- [ ] No unused bibliography entries (warn, not block).
- [ ] First mention of each acronym is the spelled-out form
  (e.g., "Large Language Model (LLM)").

### 2c. Numerical & data integrity
- [ ] Every per-model rate, per-cell rate, and aggregate rate quoted in
  prose / tables matches the value in `results/figures_of_merit.json` /
  `results/figures_of_merit_openai.json`. Run the cross-check at the
  bottom.
- [ ] All confidence intervals are 95% Wilson; no mixing of CI types.
- [ ] When comparing to paper figures, give a citation+section/table
  reference (e.g., "paper Table 2") so the reader can verify.
- [ ] N is reported alongside every rate; aggregate rates carry their CI.

### 2d. Typography & language
- [ ] All math sets `$...$` (no `\$1{,}250`-style typos for currency
  outside math mode; outside math use `\$1{,}250` with the literal `\$`).
- [ ] No double-spaces, no trailing whitespace.
- [ ] Use `--` for ranges (en-dash), `---` for em-dash; never `-` for
  ranges.
- [ ] Use `\,` for thin space (e.g., `100\,trials`) not unbreakable
  space inside numbers.
- [ ] Punctuation outside math: e.g., write "the rate, $p$, is $0.65$,"
  not "the rate, $p,$ is $0.65,$".
- [ ] Check spelling: `aspell --mode=tex check paper/main.tex`.

### 2e. Reproducibility / artifacts
- [ ] Abstract contains the GitHub link
  <https://github.com/akmaier/Paper-LLM-Ads> (or a redirect) so reviewers
  can land on the data and code.
- [ ] Section "Reproducing this work" cites the specific commit hash
  used to produce the table values in the paper.

## 3. Build & check commands

Run from the repo root:

```bash
# Compile twice for cross-references, plus bibtex.
cd paper
pdflatex -interaction=nonstopmode main.tex \
  && bibtex main \
  && pdflatex -interaction=nonstopmode main.tex \
  && pdflatex -interaction=nonstopmode main.tex

# Page-limit check.
pdftk main.pdf dump_data | grep NumberOfPages

# Overfull \hbox detection.
grep -E '^Overfull|^Underfull' main.log | grep -v '^Underfull \\vbox' \
  | head -20

# Unresolved citations / labels.
grep -E 'undefined|multiply defined|no \\citation' main.log | head

# Citation key audit.
python3 ../scripts/_audit_refs.py main.tex main.bib
```

`_audit_refs.py` prints:
- every `\cite{key}` that has no matching `@type{key,...}` entry
- every BibTeX entry that is never cited (warn-only)
- duplicate keys (block)

## 4. Pass / fail summary

The paper is ready to submit when **all checkboxes in §2 are ✓** and:
- pdfinfo shows `Pages: ≤ 15`
- `grep -E '^Overfull \\hbox' main.log` is empty
- `references_audit.md` lists every BibTeX key as `verified`
- `make spellcheck` exits 0
