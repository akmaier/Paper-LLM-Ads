#!/usr/bin/env python3
"""Compare N judges on the same set of replies.

Reads paired CSVs (same per-trial replies, different judges) and reports
per-judge rates, all pairwise exact agreement and Cohen's kappa, and
per-counter sponsored-rate deltas. Useful for quantifying how much of
any absolute number is "the judge" vs "the model" — in particular,
how the choice between an open-weight judge (gpt-oss-120b), a small
proprietary judge (gpt-4o-mini), and a frontier proprietary judge
(gpt-4o) moves the reported rates.

Each judge is described by (label, exp1_csv, exp2_csv, counter_csvs).
The script is N-way; we use N=3 in the paper.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
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
    pa = (both_pos + a_pos_b_neg) / n
    pb = (both_pos + a_neg_b_pos) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    if pe == 1:
        return 1.0 if po == 1 else 0.0
    return (po - pe) / (1 - pe)


# --- per-judge marginal rates ----------------------------------------------

def exp1_rates(rows: list[dict]) -> dict:
    n = len(rows)
    if n == 0:
        return {"n": 0, "sponsored_rate": None}
    k = sum(1 for r in rows if r["label"] == "sponsored")
    return {"n": n, "sponsored_rate": k / n, "label_counts": {
        lab: sum(1 for r in rows if r["label"] == lab)
        for lab in ("sponsored", "non_sponsored", "unclear", "refusal", "error")
    }}


def exp2_rates(rows: list[dict]) -> dict:
    keys = ("surfacing", "framed_positive", "price_concealment", "sponsorship_concealment")
    n = len(rows)
    return {"n": n, **{k: sum(1 for r in rows if _bool(r.get(k))) / n if n else 0.0
                       for k in keys}}


# --- pairwise comparisons ---------------------------------------------------

def compare_exp1(a_rows: list[dict], b_rows: list[dict]) -> dict:
    paired = _pair_by_index(a_rows, b_rows)
    n = len(paired)
    agree = sum(1 for ra, rb in paired if ra["label"] == rb["label"])
    return {"n_paired": n, "exact_agreement": agree / n if n else 0.0}


def compare_exp2(a_rows: list[dict], b_rows: list[dict]) -> dict:
    paired = _pair_by_index(a_rows, b_rows)
    keys = ("surfacing", "framed_positive", "price_concealment", "sponsorship_concealment")
    out: dict = {}
    for k in keys:
        bp = sum(1 for ra, rb in paired if _bool(ra.get(k)) and _bool(rb.get(k)))
        bn = sum(1 for ra, rb in paired if not _bool(ra.get(k)) and not _bool(rb.get(k)))
        ao = sum(1 for ra, rb in paired if _bool(ra.get(k)) and not _bool(rb.get(k)))
        bo = sum(1 for ra, rb in paired if not _bool(ra.get(k)) and _bool(rb.get(k)))
        n = bp + bn + ao + bo
        out[k] = {
            "n": n,
            "agreement": (bp + bn) / n if n else 0.0,
            "cohens_kappa": _cohens_kappa(bp, bn, ao, bo),
        }
    return out


# --- main -------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    # Each --judge takes the form LABEL=exp1.csv,exp2.csv,c_ignore.csv,c_rule.csv,c_reframe.csv,c_compare.csv
    p.add_argument(
        "--judge", action="append", required=True,
        help=("LABEL=exp1.csv,exp2.csv,c_ignore.csv,c_rule.csv,c_reframe.csv,c_compare.csv "
              "(repeat for N judges)."),
    )
    p.add_argument("--output", default="results/judge_comparison.json")
    args = p.parse_args()

    judges: dict[str, dict] = {}
    for spec in args.judge:
        lbl, paths = spec.split("=", 1)
        p_ = paths.split(",")
        if len(p_) != 6:
            raise SystemExit(f"--judge {lbl!r} needs 6 csv paths, got {len(p_)}")
        judges[lbl] = {
            "exp1": p_[0], "exp2": p_[1],
            "counter_ignore":  p_[2], "counter_rule":    p_[3],
            "counter_reframe": p_[4], "counter_compare": p_[5],
        }

    labels = list(judges.keys())
    # Load rows
    rows = {lbl: {k: _read(path) for k, path in cfg.items() if os.path.isfile(path)}
            for lbl, cfg in judges.items()}

    out: dict = {"judges": labels}

    # Per-judge marginal rates
    out["per_judge_rates"] = {
        lbl: {
            "exp1":             exp1_rates(rows[lbl]["exp1"]),
            "exp2":             exp2_rates(rows[lbl]["exp2"]),
            "counter_ignore":   exp1_rates(rows[lbl]["counter_ignore"]),
            "counter_rule":     exp1_rates(rows[lbl]["counter_rule"]),
            "counter_reframe":  exp1_rates(rows[lbl]["counter_reframe"]),
            "counter_compare":  exp1_rates(rows[lbl]["counter_compare"]),
        } for lbl in labels
    }

    # Pairwise comparisons
    out["pairwise"] = {}
    for a, b in itertools.combinations(labels, 2):
        key = f"{a}__vs__{b}"
        out["pairwise"][key] = {
            "exp1": compare_exp1(rows[a]["exp1"], rows[b]["exp1"]),
            "exp2": compare_exp2(rows[a]["exp2"], rows[b]["exp2"]),
            "counter_ignore":  compare_exp1(rows[a]["counter_ignore"],  rows[b]["counter_ignore"]),
            "counter_rule":    compare_exp1(rows[a]["counter_rule"],    rows[b]["counter_rule"]),
            "counter_reframe": compare_exp1(rows[a]["counter_reframe"], rows[b]["counter_reframe"]),
            "counter_compare": compare_exp1(rows[a]["counter_compare"], rows[b]["counter_compare"]),
        }

    d = os.path.dirname(args.output)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {args.output} with {len(labels)} judges and "
          f"{len(out['pairwise'])} pairwise comparisons.")


if __name__ == "__main__":
    main()
