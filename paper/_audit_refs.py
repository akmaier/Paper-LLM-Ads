#!/usr/bin/env python3
"""Audit citations in main.tex against entries in main.bib.

Prints:
  - every \\cite{key} in main.tex with no matching @TYPE{key,...} in main.bib (FAIL)
  - every entry in main.bib that is never cited (warn)
  - duplicate keys in main.bib (FAIL)
  - keys with no URL/DOI/arXiv reference (warn — verify these by hand)
"""
from __future__ import annotations
import re, sys

def cite_keys(tex_path):
    with open(tex_path) as f: text = f.read()
    out = set()
    for m in re.finditer(r"\\cite[a-zA-Z]*\{([^}]+)\}", text):
        for k in m.group(1).split(","):
            k = k.strip()
            if k: out.add(k)
    return out

def bib_entries(bib_path):
    with open(bib_path) as f: text = f.read()
    keys = []
    body = {}
    for m in re.finditer(r"^@(\w+)\{([^,\s]+)\s*,\s*(.*?)^\}", text, re.DOTALL | re.MULTILINE):
        kind, key, fields = m.group(1), m.group(2), m.group(3)
        keys.append(key)
        body[key] = fields
    return keys, body

def main(tex, bib):
    cites = cite_keys(tex)
    keys, body = bib_entries(bib)
    bib_set = set(keys)
    fail = 0
    miss = sorted(cites - bib_set)
    if miss:
        print(f"FAIL: {len(miss)} citations have no bib entry:")
        for k in miss: print(f"  {k}")
        fail += 1
    unused = sorted(bib_set - cites)
    if unused:
        print(f"warn: {len(unused)} bib entries are never cited: {', '.join(unused)}")
    dups = [k for k in keys if keys.count(k) > 1]
    if dups:
        print(f"FAIL: duplicate bib keys: {set(dups)}")
        fail += 1
    no_url = []
    for k in sorted(bib_set):
        f = body[k]
        if not re.search(r"\b(url|doi|arxiv)\b\s*=", f, re.IGNORECASE):
            no_url.append(k)
    if no_url:
        print(f"warn: {len(no_url)} bib entries lack url/doi/arxiv (verify by hand): {', '.join(no_url)}")
    if not fail:
        print(f"OK: {len(cites)} citations, all resolved against {len(bib_set)} bib entries.")
    sys.exit(1 if fail else 0)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "main.tex",
         sys.argv[2] if len(sys.argv) > 2 else "main.bib")
