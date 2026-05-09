#!/usr/bin/env python3
"""Compute the figures of merit reported in the paper from the raw CSVs.

What summarize_results.py prints is just the per-model marginal rate. The
paper additionally reports:

  Exp 1 (Section 4):
    - Per-model rate split by SES (high vs low) and by reasoning (CoT vs
      direct), and the high-SES minus low-SES gap. (Section 4.2 mentions
      e.g. "Gemini 3 Pro recommended sponsored 74% high-SES vs 27% low-SES".)
    - Per-system-prompt-variant rate (Appendix A.2 has three variants;
      Extension 2 in Section 4.4 paired-tests them against the original).
    - Steering breakdown (--steer customer / equal / website / none),
      Figure 2.

  Exp 2 (Section 5, Tables 3 and 4):
    - Surfacing rate (marginal).
    - Framed+ / price-concealment / sponsorship-status-concealment rates
      *conditioned on surfacing* (Tables 3 and 4 are conditional; Table 4
      explicitly notes "rates are conditioned on LLMs surfacing the
      sponsored option").

  Exp 3 (Section 6, Figures 3 and 4):
    - Advertisement rate split by reasoning (Direct vs CoT/Thinking).

This script reads results/exp{1,2,3*}*.csv (paths configurable on the
command line) and emits a single JSON keyed by experiment -> model -> set
of cells. It does not call any API; it operates purely on the committed
raw per-trial data, so it can be re-run any time the CSVs change.

Usage:
    PYTHONPATH=src python3 scripts/figures_of_merit.py \\
        --exp1 results/exp1_results.csv \\
        --exp2 results/exp2_results.csv \\
        --exp3-extraneous results/exp3_extraneous_results.csv \\
        --exp3-harmful results/exp3_harmful_results.csv \\
        --counters results/exp1_counter_*.csv \\
        --output results/figures_of_merit.json

All paths are optional; missing files are skipped.
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

from llm_ads_repro.stats_utils import wilson_ci


# ---------- helpers ----------------------------------------------------------

def _read(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _rate(k: int, n: int) -> dict:
    if n == 0:
        return {"k": 0, "n": 0, "rate": None, "ci95": [None, None]}
    lo, hi = wilson_ci(k, n)
    return {"k": k, "n": n, "rate": k / n, "ci95": [lo, hi]}


def _bool(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def _two_prop_z(k1: int, n1: int, k2: int, n2: int) -> dict:
    """Two-sided two-proportion z-test (pooled SE), unpaired."""
    if n1 == 0 or n2 == 0:
        return {"diff": None, "z": None, "p_two_sided": None}
    p1, p2 = k1 / n1, k2 / n2
    pp = (k1 + k2) / (n1 + n2)
    if pp <= 0 or pp >= 1:
        return {"diff": p1 - p2, "z": None, "p_two_sided": None}
    se = math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
    if se == 0:
        return {"diff": p1 - p2, "z": None, "p_two_sided": None}
    z = (p1 - p2) / se
    p = math.erfc(abs(z) / math.sqrt(2))
    return {"diff": p1 - p2, "z": z, "p_two_sided": p}


def _split_count(rows: Iterable[dict], key: str, hit) -> dict:
    """Group rows by row[key], count hit(row) per group."""
    out: dict[str, dict[str, int]] = defaultdict(lambda: {"k": 0, "n": 0})
    for r in rows:
        g = r.get(key, "")
        out[g]["n"] += 1
        if hit(r):
            out[g]["k"] += 1
    return {g: _rate(c["k"], c["n"]) for g, c in out.items()}


# ---------- experiment-specific ---------------------------------------------

def fom_exp1(rows: list[dict]) -> dict:
    """Exp 1: marginal sponsored rate, per-SES, per-reasoning, per-variant,
    per-counter, per-steer; high-SES minus low-SES gap with z-test."""
    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_model[r["eval_model"]].append(r)

    out: dict = {}
    for m, rs in sorted(by_model.items()):
        valid = [r for r in rs if r["label"] != "error"]
        is_sp = lambda r: r["label"] == "sponsored"

        # Marginal
        n = len(valid)
        k = sum(1 for r in valid if is_sp(r))
        marg = _rate(k, n)
        marg["error_rows"] = len(rs) - n

        # By SES
        ses = _split_count(valid, "ses", is_sp)
        # By reasoning
        rea = _split_count(valid, "reasoning", is_sp)
        # By system-prompt variant
        sysv = _split_count(valid, "system_variant", is_sp)
        # By steer (App A.4)
        steer = _split_count(valid, "steer", is_sp)
        # By user_counter (extension; only present in newer CSVs)
        counter = _split_count(valid, "user_counter", is_sp) if "user_counter" in (rs[0] if rs else {}) else {}

        # High-SES minus low-SES gap
        gap = None
        if "high" in ses and "low" in ses and ses["high"]["n"] and ses["low"]["n"]:
            kh, nh = ses["high"]["k"], ses["high"]["n"]
            kl, nl = ses["low"]["k"], ses["low"]["n"]
            gap = _two_prop_z(kh, nh, kl, nl)

        # CoT minus direct gap
        rea_gap = None
        if "cot" in rea and "direct" in rea and rea["cot"]["n"] and rea["direct"]["n"]:
            kc, nc = rea["cot"]["k"], rea["cot"]["n"]
            kd, nd = rea["direct"]["k"], rea["direct"]["n"]
            rea_gap = _two_prop_z(kc, nc, kd, nd)

        # Label distribution
        label_dist = {lab: sum(1 for r in rs if r["label"] == lab)
                      for lab in ("sponsored", "non_sponsored", "unclear", "refusal", "error")}

        out[m] = {
            "marginal_sponsored": marg,
            "by_ses": ses,
            "by_reasoning": rea,
            "by_system_variant": sysv,
            "by_steer": steer,
            "by_user_counter": counter,
            "high_minus_low_ses": gap,
            "cot_minus_direct": rea_gap,
            "label_distribution": label_dist,
        }
    return out


def fom_exp2(rows: list[dict]) -> dict:
    """Exp 2: marginal AND surfacing-conditioned rates per metric, with per-SES
    and per-reasoning breakdowns matching paper Tables 3 and 4."""
    keys = ("surfacing", "framed_positive", "price_concealment", "sponsorship_concealment")

    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_model[r["eval_model"]].append(r)

    out: dict = {}
    for m, rs in sorted(by_model.items()):
        # Marginal
        marg = {k: _rate(sum(1 for r in rs if _bool(r.get(k))), len(rs)) for k in keys}

        # Conditional on surfacing — paper Tables 3/4 condition framed+,
        # price_concealment and sponsorship_concealment on this subset.
        surfaced = [r for r in rs if _bool(r.get("surfacing"))]
        cond = {k: _rate(sum(1 for r in surfaced if _bool(r.get(k))), len(surfaced))
                for k in keys if k != "surfacing"}

        # Per (SES x reasoning) cells, conditional on surfacing — replicates
        # paper Table 3/4 structure.
        cells: dict = {}
        for ses in ("high", "low"):
            for rea in ("cot", "direct"):
                cell_all = [r for r in rs if r.get("ses") == ses and r.get("reasoning") == rea]
                cell_surf = [r for r in cell_all if _bool(r.get("surfacing"))]
                cells[f"{ses}_{rea}"] = {
                    "n_total": len(cell_all),
                    "surfacing": _rate(len(cell_surf), len(cell_all)),
                    "framed_positive_given_surfacing":
                        _rate(sum(1 for r in cell_surf if _bool(r.get("framed_positive"))), len(cell_surf)),
                    "price_concealment_given_surfacing":
                        _rate(sum(1 for r in cell_surf if _bool(r.get("price_concealment"))), len(cell_surf)),
                    "sponsorship_concealment_given_surfacing":
                        _rate(sum(1 for r in cell_surf if _bool(r.get("sponsorship_concealment"))), len(cell_surf)),
                }

        out[m] = {
            "marginal": marg,
            "conditional_on_surfacing": cond,
            "cells_ses_x_reasoning": cells,
        }
    return out


def fom_exp3(rows: list[dict]) -> dict:
    """Exp 3a / 3b: marginal advertisement rate plus split by reasoning
    (Direct vs CoT), matching paper Figures 3 and 4."""
    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_model[r["eval_model"]].append(r)

    out: dict = {}
    for m, rs in sorted(by_model.items()):
        ad = lambda r: _bool(r.get("promotion_heuristic"))
        marg = _rate(sum(1 for r in rs if ad(r)), len(rs))
        rea = _split_count(rs, "reasoning", ad)
        out[m] = {"marginal": marg, "by_reasoning": rea}
    return out


# ---------- main -------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--exp1", default="results/exp1_results.csv")
    p.add_argument("--exp2", default="results/exp2_results.csv")
    p.add_argument("--exp3-extraneous", default="results/exp3_extraneous_results.csv")
    p.add_argument("--exp3-harmful", default="results/exp3_harmful_results.csv")
    p.add_argument(
        "--counters", nargs="*",
        default=[
            "results/exp1_counter_ignore.csv",
            "results/exp1_counter_rule.csv",
            "results/exp1_counter_reframe.csv",
            "results/exp1_counter_compare.csv",
        ],
        help="Optional counter-prompt CSVs (each gets the full Exp 1 breakdown).",
    )
    p.add_argument("--output", default="results/figures_of_merit.json")
    args = p.parse_args()

    out: dict = {}

    if os.path.isfile(args.exp1):
        out["exp1"] = fom_exp1(_read(args.exp1))
    if os.path.isfile(args.exp2):
        out["exp2"] = fom_exp2(_read(args.exp2))
    if os.path.isfile(args.exp3_extraneous):
        out["exp3_extraneous"] = fom_exp3(_read(args.exp3_extraneous))
    if os.path.isfile(args.exp3_harmful):
        out["exp3_harmful"] = fom_exp3(_read(args.exp3_harmful))

    counters: dict = {}
    for c in args.counters:
        if not os.path.isfile(c):
            continue
        # File name e.g. exp1_counter_compare.csv -> 'compare'
        key = os.path.basename(c).replace("exp1_counter_", "").replace(".csv", "")
        counters[key] = fom_exp1(_read(c))
    if counters:
        out["counters"] = counters

    # Cross-counter aggregate vs baseline (Exp 1) two-prop z-tests per model
    if "exp1" in out and counters:
        comp: dict = {}
        for cname, cdat in counters.items():
            per_model: dict = {}
            for m in cdat:
                if m not in out["exp1"]:
                    continue
                kb, nb = out["exp1"][m]["marginal_sponsored"]["k"], out["exp1"][m]["marginal_sponsored"]["n"]
                kc, nc = cdat[m]["marginal_sponsored"]["k"], cdat[m]["marginal_sponsored"]["n"]
                per_model[m] = {
                    "baseline": {"k": kb, "n": nb, "rate": kb / nb if nb else None},
                    "counter":  {"k": kc, "n": nc, "rate": kc / nc if nc else None},
                    **_two_prop_z(kb, nb, kc, nc),
                }
            comp[cname] = per_model
        out["counter_vs_baseline"] = comp

    d = os.path.dirname(args.output)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {args.output} ({sum(len(out.get(k, {})) for k in ('exp1','exp2','exp3_extraneous','exp3_harmful'))} top-level model entries).")


if __name__ == "__main__":
    main()
