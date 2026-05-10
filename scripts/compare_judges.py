#!/usr/bin/env python3
"""Compare two judges on the same set of replies.

Reads paired CSVs (same per-trial replies, two different judges) and
reports per-metric agreement plus per-model rate deltas. Useful for
quantifying how much of any absolute number is "the judge" vs "the
model" — a question raised when our `gpt-oss-120b` judge labels
diverged sharply from the paper's GPT-4o judge on Experiment 2.

Usage:
    PYTHONPATH=src python3 scripts/compare_judges.py \\
        --exp1-a results/exp1_results.csv \\
        --exp1-b results/exp1_results.gpt-4o-mini.csv \\
        --exp2-a results/exp2_results.csv \\
        --exp2-b results/exp2_results.gpt-4o-mini.csv \\
        --counters-a results/exp1_counter_*.csv \\
        --counters-b results/exp1_counter_*.gpt-4o-mini.csv \\
        --output results/judge_comparison.json

The two judges are referenced as A (the file passed to the *-a flag)
and B (the *-b flag). The script does not assume one is "right"; it
reports raw agreement and delta in either direction.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict
from typing import Iterable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def _read(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _bool(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def _pair_by_index(a: list[dict], b: list[dict]) -> list[tuple[dict, dict]]:
    """Pair rows by (eval_model, trial_index). The two CSVs were produced
    from the same per-trial sample, so this matches reliably."""
    bi = {(r["eval_model"], int(r["trial_index"])): r for r in b}
    out: list[tuple[dict, dict]] = []
    for ra in a:
        key = (ra["eval_model"], int(ra["trial_index"]))
        rb = bi.get(key)
        if rb is not None:
            out.append((ra, rb))
    return out


def _cohens_kappa(both_pos: int, both_neg: int, a_pos_b_neg: int, a_neg_b_pos: int) -> float | None:
    n = both_pos + both_neg + a_pos_b_neg + a_neg_b_pos
    if n == 0:
        return None
    po = (both_pos + both_neg) / n
    pa = (both_pos + a_pos_b_neg) / n  # P(A=1)
    pb = (both_pos + a_neg_b_pos) / n  # P(B=1)
    pe = pa * pb + (1 - pa) * (1 - pb)
    if pe == 1:
        return 1.0 if po == 1 else 0.0
    return (po - pe) / (1 - pe)


def compare_exp1(a_rows: list[dict], b_rows: list[dict]) -> dict:
    """Compare 4-class label distributions (sponsored/non_sponsored/unclear/refusal)."""
    paired = _pair_by_index(a_rows, b_rows)
    n = len(paired)
    agree = sum(1 for ra, rb in paired if ra["label"] == rb["label"])
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for ra, rb in paired:
        confusion[ra["label"]][rb["label"]] += 1

    # Per-model sponsored-rate deltas, with two-prop z-test
    by_model: dict[str, dict] = defaultdict(lambda: {"a_k": 0, "b_k": 0, "n": 0})
    for ra, rb in paired:
        m = ra["eval_model"]
        by_model[m]["n"] += 1
        if ra["label"] == "sponsored": by_model[m]["a_k"] += 1
        if rb["label"] == "sponsored": by_model[m]["b_k"] += 1

    per_model = {}
    for m, d in by_model.items():
        # paired difference: McNemar would be more correct, but the two
        # judges see the same replies so the simpler delta is
        # interpretable for the user-facing summary.
        a_rate = d["a_k"] / d["n"] if d["n"] else 0.0
        b_rate = d["b_k"] / d["n"] if d["n"] else 0.0
        per_model[m] = {
            "n": d["n"],
            "a_sponsored": d["a_k"], "b_sponsored": d["b_k"],
            "a_rate": a_rate, "b_rate": b_rate,
            "delta_b_minus_a": b_rate - a_rate,
        }

    return {
        "n_paired": n,
        "exact_agreement": agree / n if n else 0.0,
        "confusion_a_to_b": {k: dict(v) for k, v in confusion.items()},
        "per_model": per_model,
    }


def compare_exp2(a_rows: list[dict], b_rows: list[dict]) -> dict:
    """Per-metric Cohen's κ + per-model marginal rate delta."""
    paired = _pair_by_index(a_rows, b_rows)
    keys = ("surfacing", "framed_positive", "price_concealment", "sponsorship_concealment")
    out_metrics: dict = {}
    for k in keys:
        both_pos = sum(1 for ra, rb in paired if _bool(ra.get(k)) and _bool(rb.get(k)))
        both_neg = sum(1 for ra, rb in paired if not _bool(ra.get(k)) and not _bool(rb.get(k)))
        a_only = sum(1 for ra, rb in paired if _bool(ra.get(k)) and not _bool(rb.get(k)))
        b_only = sum(1 for ra, rb in paired if not _bool(ra.get(k)) and _bool(rb.get(k)))
        n = both_pos + both_neg + a_only + b_only
        out_metrics[k] = {
            "n": n,
            "a_rate": (both_pos + a_only) / n if n else 0.0,
            "b_rate": (both_pos + b_only) / n if n else 0.0,
            "agreement": (both_pos + both_neg) / n if n else 0.0,
            "cohens_kappa": _cohens_kappa(both_pos, both_neg, a_only, b_only),
        }

    by_model: dict[str, dict] = defaultdict(lambda: {"n": 0, **{f"a_{k}": 0 for k in keys}, **{f"b_{k}": 0 for k in keys}})
    for ra, rb in paired:
        m = ra["eval_model"]; by_model[m]["n"] += 1
        for k in keys:
            if _bool(ra.get(k)): by_model[m][f"a_{k}"] += 1
            if _bool(rb.get(k)): by_model[m][f"b_{k}"] += 1
    per_model = {}
    for m, d in by_model.items():
        per_model[m] = {"n": d["n"]}
        for k in keys:
            ar = d[f"a_{k}"] / d["n"] if d["n"] else 0.0
            br = d[f"b_{k}"] / d["n"] if d["n"] else 0.0
            per_model[m][k] = {"a_rate": ar, "b_rate": br, "delta_b_minus_a": br - ar}
    return {"per_metric": out_metrics, "per_model": per_model}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--exp1-a", default="results/exp1_results.csv")
    p.add_argument("--exp1-b", default="results/exp1_results.gpt-4o-mini.csv")
    p.add_argument("--exp2-a", default="results/exp2_results.csv")
    p.add_argument("--exp2-b", default="results/exp2_results.gpt-4o-mini.csv")
    p.add_argument("--counters-a", nargs="*", default=[
        "results/exp1_counter_ignore.csv",
        "results/exp1_counter_rule.csv",
        "results/exp1_counter_reframe.csv",
        "results/exp1_counter_compare.csv",
    ])
    p.add_argument("--counters-b", nargs="*", default=[
        "results/exp1_counter_ignore.gpt-4o-mini.csv",
        "results/exp1_counter_rule.gpt-4o-mini.csv",
        "results/exp1_counter_reframe.gpt-4o-mini.csv",
        "results/exp1_counter_compare.gpt-4o-mini.csv",
    ])
    p.add_argument("--output", default="results/judge_comparison.json")
    p.add_argument("--label-a", default="gpt-oss-120b")
    p.add_argument("--label-b", default="gpt-4o-mini")
    args = p.parse_args()

    out: dict = {"judge_a": args.label_a, "judge_b": args.label_b}

    if os.path.isfile(args.exp1_a) and os.path.isfile(args.exp1_b):
        out["exp1"] = compare_exp1(_read(args.exp1_a), _read(args.exp1_b))
    if os.path.isfile(args.exp2_a) and os.path.isfile(args.exp2_b):
        out["exp2"] = compare_exp2(_read(args.exp2_a), _read(args.exp2_b))
    if len(args.counters_a) == len(args.counters_b):
        cmp: dict = {}
        for a, b in zip(args.counters_a, args.counters_b):
            if not (os.path.isfile(a) and os.path.isfile(b)):
                continue
            key = os.path.basename(a).replace("exp1_counter_", "").replace(".csv", "")
            cmp[key] = compare_exp1(_read(a), _read(b))
        if cmp:
            out["counters"] = cmp

    d = os.path.dirname(args.output)
    if d: os.makedirs(d, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
