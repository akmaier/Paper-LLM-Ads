#!/usr/bin/env python3
"""Aggregate the multi-seed rebuttal runs (R2.1) into per-seed pooled rates.

All rates are pooled over the NINE open-weight models that the rebuttal
runs cover (IBM/granite-4.0-micro was retired from the gateway), so seed 0
is recomputed on the same nine-model subset for an apples-to-apples
comparison. Seed 0 comes from the committed gpt-oss-120b-judged artifacts
(counter_comparison.json for Exp1 baseline+compare, exp3_harmful_results.csv
for Exp3b); seeds 1-3 come from results/rebuttal/*.csv. Reports per-seed
pooled rate, mean, and sample standard deviation for: Exp1 baseline
sponsored rate, Exp1 `compare` counter rate, Exp3b promotion-heuristic rate.
Prints both a JSON blob and a LaTeX tabular body.
"""
from __future__ import annotations

import csv
import json
import os
import statistics
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
REB = os.path.join(ROOT, "results", "rebuttal")

# Nine models the rebuttal seeds cover (granite excluded).
MODELS = {
    "GaleneAI/Magistral-Small-2509-FP8-Dynamic",
    "Microsoft/Phi-4-mini-instruct",
    "Qwen/Qwen3.5-9B",
    "Qwen/Qwen3.6-35B-A3B-FP8",
    "Qwen3-VL-8B-Instruct",
    "RedHatAI/Mistral-Small-3.2-24B-Instruct-2506-FP8",
    "RedHatAI/gemma-3-27b-it-quantized.w4a16",
    "google/gemma-4-E4B-it",
    "gpt-oss-120b",
}


def _read(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def exp1_rate_from_csv(path: str) -> tuple[int, int]:
    """Return (sponsored, n_nonerror) pooled over MODELS."""
    spons = nonerr = 0
    for r in _read(path):
        if r.get("eval_model") not in MODELS:
            continue
        lab = (r.get("label") or "").strip().lower()
        reply = r.get("reply") or ""
        if lab.startswith("error") or reply.startswith("ERROR:"):
            continue
        nonerr += 1
        if lab == "sponsored":
            spons += 1
    return spons, nonerr


def exp3b_rate_from_csv(path: str) -> tuple[int, int]:
    pos = nonerr = 0
    for r in _read(path):
        if r.get("eval_model") not in MODELS:
            continue
        reply = r.get("reply") or ""
        if reply.startswith("ERROR:"):
            continue
        nonerr += 1
        if str(r.get("promotion_heuristic")).strip().lower() in ("true", "1", "yes"):
            pos += 1
    return pos, nonerr


def seed0_from_counter_json(key: str) -> tuple[int, int]:
    d = json.load(open(os.path.join(ROOT, "results", "counter_comparison.json")))
    block = d[key]
    spons = sum(v["spons"] for m, v in block.items() if m in MODELS)
    n = sum(v["n"] - v.get("errs", 0) for m, v in block.items() if m in MODELS)
    return spons, n


def pct(num: int, den: int) -> float:
    return 100.0 * num / den if den else float("nan")


def collect(metric: str) -> dict:
    rows = {}
    for s in (1, 2, 3):
        if metric == "baseline":
            p = os.path.join(REB, f"exp1_seed{s}.csv")
            if os.path.isfile(p):
                rows[s] = exp1_rate_from_csv(p)
        elif metric == "compare":
            p = os.path.join(REB, f"exp1_compare_seed{s}.csv")
            if os.path.isfile(p):
                rows[s] = exp1_rate_from_csv(p)
        elif metric == "exp3b":
            p = os.path.join(REB, f"exp3_harmful_seed{s}.csv")
            if os.path.isfile(p):
                rows[s] = exp3b_rate_from_csv(p)
    # seed 0
    if metric == "baseline":
        rows[0] = seed0_from_counter_json("baseline")
    elif metric == "compare":
        rows[0] = seed0_from_counter_json("compare")
    elif metric == "exp3b":
        rows[0] = exp3b_rate_from_csv(
            os.path.join(ROOT, "results", "exp3_harmful_results.csv"))
    return rows


def main() -> None:
    out = {"n_models": len(MODELS), "metrics": {}}
    for metric in ("baseline", "compare", "exp3b"):
        rows = collect(metric)
        per_seed = {s: {"num": n, "den": d, "rate_pct": pct(n, d)}
                    for s, (n, d) in sorted(rows.items())}
        rates = [v["rate_pct"] for v in per_seed.values()]
        out["metrics"][metric] = {
            "per_seed": per_seed,
            "mean_pct": statistics.mean(rates) if rates else None,
            "sd_pct": statistics.pstdev(rates) if len(rates) > 1 else None,
            "sample_sd_pct": statistics.stdev(rates) if len(rates) > 1 else None,
            "min_pct": min(rates) if rates else None,
            "max_pct": max(rates) if rates else None,
            "n_seeds": len(rates),
        }
    print(json.dumps(out, indent=2))

    # LaTeX tabular body: one row per seed with the three rates.
    seeds = sorted({s for m in out["metrics"].values() for s in m["per_seed"]})
    print("\n% --- LaTeX tabular body (seed & baseline & compare & exp3b) ---")
    for s in seeds:
        def cell(metric):
            ps = out["metrics"][metric]["per_seed"].get(s)
            return f"{ps['rate_pct']:.1f}" if ps else "--"
        print(f"{s} & {cell('baseline')} & {cell('compare')} & {cell('exp3b')} \\\\")
    print("\\midrule")
    def stat(metric, key):
        v = out["metrics"][metric][key]
        return f"{v:.1f}" if v is not None else "--"
    print(f"mean & {stat('baseline','mean_pct')} & {stat('compare','mean_pct')} & {stat('exp3b','mean_pct')} \\\\")
    print(f"SD & {stat('baseline','sample_sd_pct')} & {stat('compare','sample_sd_pct')} & {stat('exp3b','sample_sd_pct')} \\\\")

    with open(os.path.join(ROOT, "results", "seed_robustness.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
