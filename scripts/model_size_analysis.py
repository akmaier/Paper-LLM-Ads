#!/usr/bin/env python3
"""Model size vs. behaviour analysis (reviewer concern R2.3).

Tests whether the per-model rates follow a simple parameter-count trend.
Reads the gpt-4o-judged figures_of_merit.json for the Exp 1 sponsored rate
and the (judge-independent) Exp 3a / Exp 3b heuristic rates, attaches each
open-weight model's nominal total parameter count, and reports Spearman and
Pearson correlations between size and each behaviour.

For mixture-of-experts models (Qwen3.6-35B-A3B with 3B active, gpt-oss-120b
with ~5B active) we use TOTAL parameters as the nominal size; Spearman is
rank-based and so is insensitive to the exact value, and the conclusion
(no monotone trend) is unchanged if active counts are substituted.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from scipy.stats import pearsonr, spearmanr

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Nominal total parameter count in billions. Sources: model cards / official
# release notes. E4B = Gemma's effective-4B MatFormer; A3B = 3B active MoE.
MODEL_SIZE_B = {
    "IBM/granite-4.0-micro": 3.0,
    "Microsoft/Phi-4-mini-instruct": 3.8,
    "google/gemma-4-E4B-it": 4.0,
    "Qwen3-VL-8B-Instruct": 8.0,
    "Qwen/Qwen3.5-9B": 9.0,
    "GaleneAI/Magistral-Small-2509-FP8-Dynamic": 24.0,
    "RedHatAI/Mistral-Small-3.2-24B-Instruct-2506-FP8": 24.0,
    "RedHatAI/gemma-3-27b-it-quantized.w4a16": 27.0,
    "Qwen/Qwen3.6-35B-A3B-FP8": 35.0,
    "gpt-oss-120b": 120.0,
}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fom", default="results/figures_of_merit.json")
    p.add_argument("--exp3a", default="results/figures_of_merit.json")
    p.add_argument("--output", default="results/model_size_analysis.json")
    args = p.parse_args()

    fom = json.load(open(args.fom))
    exp1 = fom["exp1"]
    exp3a = fom.get("exp3_extraneous", {})
    exp3b = fom.get("exp3_harmful", {})

    rows = []
    for m, size in MODEL_SIZE_B.items():
        rows.append({
            "model": m,
            "size_b": size,
            "exp1_sponsored": exp1[m]["marginal_sponsored"]["rate"] if m in exp1 else None,
            "exp3a": exp3a[m]["marginal"]["rate"] if m in exp3a else None,
            "exp3b": exp3b[m]["marginal"]["rate"] if m in exp3b else None,
        })

    out = {"per_model": rows, "correlations": {}}
    sizes = [r["size_b"] for r in rows]
    for metric in ("exp1_sponsored", "exp3a", "exp3b"):
        ys = [r[metric] for r in rows]
        pairs = [(s, y) for s, y in zip(sizes, ys) if y is not None]
        if len(pairs) < 3:
            continue
        xs, yy = zip(*pairs)
        rho, prho = spearmanr(xs, yy)
        rp, pp = pearsonr(xs, yy)
        out["correlations"][metric] = {
            "n": len(pairs),
            "spearman_rho": rho, "spearman_p": prho,
            "pearson_r": rp, "pearson_p": pp,
        }

    d = os.path.dirname(args.output)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
