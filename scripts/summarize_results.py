#!/usr/bin/env python3
"""Per-model summary tables for the four experiments.

Reads any of the result CSVs under `results/` (paths can be passed as args)
and prints model-by-model rates with 95% Wilson CIs.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from llm_ads_repro.stats_utils import wilson_ci


def _read(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def summarize_exp1(rows: list[dict]) -> dict:
    by_model: dict[str, dict[str, int]] = defaultdict(
        lambda: {"n": 0, "sponsored": 0, "non_sponsored": 0, "unclear": 0, "refusal": 0, "error": 0}
    )
    for r in rows:
        m = r["eval_model"]
        lab = r["label"]
        by_model[m]["n"] += 1
        if lab in by_model[m]:
            by_model[m][lab] += 1
    out: dict = {}
    for m, c in sorted(by_model.items()):
        valid = c["n"] - c["error"]
        rate = c["sponsored"] / valid if valid else 0.0
        lo, hi = wilson_ci(c["sponsored"], valid)
        out[m] = {
            "n_total": c["n"],
            "n_valid": valid,
            "sponsored": c["sponsored"],
            "non_sponsored": c["non_sponsored"],
            "unclear": c["unclear"],
            "refusal": c["refusal"],
            "error": c["error"],
            "sponsored_rate": round(rate, 4),
            "ci95": [round(lo, 4), round(hi, 4)],
        }
    return out


def _bool(v: str) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def summarize_exp2(rows: list[dict]) -> dict:
    keys = ("surfacing", "framed_positive", "price_concealment", "sponsorship_concealment")
    by_model: dict[str, dict] = defaultdict(lambda: {"n": 0, **{k: 0 for k in keys}})
    for r in rows:
        m = r["eval_model"]
        by_model[m]["n"] += 1
        for k in keys:
            if _bool(r.get(k, "")):
                by_model[m][k] += 1
    out: dict = {}
    for m, c in sorted(by_model.items()):
        n = c["n"]
        rates = {}
        for k in keys:
            r = c[k] / n if n else 0.0
            lo, hi = wilson_ci(c[k], n)
            rates[k] = {"rate": round(r, 4), "ci95": [round(lo, 4), round(hi, 4)], "k": c[k]}
        out[m] = {"n": n, **rates}
    return out


def summarize_exp3(rows: list[dict]) -> dict:
    by_model: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "ad": 0})
    for r in rows:
        m = r["eval_model"]
        by_model[m]["n"] += 1
        if _bool(r.get("promotion_heuristic", "")):
            by_model[m]["ad"] += 1
    out: dict = {}
    for m, c in sorted(by_model.items()):
        n = c["n"]
        r = c["ad"] / n if n else 0.0
        lo, hi = wilson_ci(c["ad"], n)
        out[m] = {
            "n": n,
            "promotion": c["ad"],
            "promotion_rate": round(r, 4),
            "ci95": [round(lo, 4), round(hi, 4)],
        }
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "csvs",
        nargs="*",
        default=[
            "results/exp1_results.csv",
            "results/exp2_results.csv",
            "results/exp3_extraneous_results.csv",
            "results/exp3_harmful_results.csv",
        ],
    )
    args = p.parse_args()
    out: dict = {}
    for c in args.csvs:
        if not os.path.isfile(c):
            out[c] = {"missing": True}
            continue
        rows = _read(c)
        base = os.path.basename(c)
        if "exp1" in base:
            out[c] = summarize_exp1(rows)
        elif "exp2" in base:
            out[c] = summarize_exp2(rows)
        elif "exp3" in base:
            out[c] = summarize_exp3(rows)
        else:
            out[c] = {"unknown_schema": True, "n_rows": len(rows)}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
