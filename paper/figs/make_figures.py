#!/usr/bin/env python3
"""Generate paper figures from the committed JSON results."""
import json, os, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RES  = ROOT / "results"
OUT  = Path(__file__).resolve().parent

plt.rcParams.update({
    "font.size": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 200,
})


def fig_counter_effect():
    """Per-model sponsored rate under baseline + 4 counters (15 conditions)."""
    fom_gw = json.load(open(RES / "figures_of_merit.json"))
    fom_oa = json.load(open(RES / "figures_of_merit_openai.json"))

    short = {
        "GaleneAI/Magistral-Small-2509-FP8-Dynamic":     "Magistral-S-2509",
        "IBM/granite-4.0-micro":                         "granite-4.0",
        "Microsoft/Phi-4-mini-instruct":                 "Phi-4-mini",
        "Qwen/Qwen3.5-9B":                               "Qwen3.5-9B",
        "Qwen/Qwen3.6-35B-A3B-FP8":                      "Qwen3.6-35B",
        "Qwen3-VL-8B-Instruct":                          "Qwen3-VL-8B",
        "RedHatAI/Mistral-Small-3.2-24B-Instruct-2506-FP8": "Mistral-S-3.2",
        "RedHatAI/gemma-3-27b-it-quantized.w4a16":       "gemma-3-27b",
        "google/gemma-4-E4B-it":                         "gemma-4-E4B",
        "gpt-oss-120b":                                  "gpt-oss-120b",
        "gpt-3.5-turbo":                                 "gpt-3.5-turbo",
        "gpt-4o":                                        "gpt-4o",
    }
    order = list(short.keys())

    counters = ("ignore", "rule", "reframe", "compare")
    base = {m: fom_gw["exp1"][m]["marginal_sponsored"]["rate"]
            for m in fom_gw["exp1"]}
    base.update({m: fom_oa["exp1"][m]["marginal_sponsored"]["rate"]
                 for m in fom_oa["exp1"]})
    cnt = {c: {m: fom_gw["counters"][c][m]["marginal_sponsored"]["rate"]
               for m in fom_gw["counters"][c]} for c in counters}
    for c in counters:
        # OpenAI keys are suffixed `_openai` because figures_of_merit.py
        # derives the dict key from the filename.
        oa_key = f"{c}_openai"
        if oa_key in fom_oa.get("counters", {}):
            cnt[c].update({m: fom_oa["counters"][oa_key][m]["marginal_sponsored"]["rate"]
                           for m in fom_oa["counters"][oa_key]})

    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    x = np.arange(len(order))
    w = 0.16
    series = [
        ("baseline", base, "#444444"),
        ("ignore",   cnt["ignore"],   "#1f77b4"),
        ("rule",     cnt["rule"],     "#2ca02c"),
        ("reframe",  cnt["reframe"],  "#ff7f0e"),
        ("compare",  cnt["compare"],  "#d62728"),
    ]
    for i, (lbl, d, c) in enumerate(series):
        vals = [d.get(m, 0.0) for m in order]
        ax.bar(x + (i - 2) * w, vals, w, label=lbl, color=c, edgecolor="white", linewidth=0.4)
    ax.axvline(9.5, color="black", lw=0.5, ls="--", alpha=0.5)
    ax.text(4.5, 1.04, "ten open-source models", ha="center", fontsize=8)
    ax.text(10.5, 1.04, "two OpenAI models", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([short[m] for m in order], rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("sponsored-recommendation rate")
    ax.set_ylim(0, 1.1)
    ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.32),
              frameon=False, fontsize=8, columnspacing=1.0, handlelength=1.5)
    ax.grid(axis="y", lw=0.3, alpha=0.5)
    fig.tight_layout()
    fig.savefig(OUT / "counter_effect.pdf", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def fig_judge_agreement():
    """Cohen's kappa for Exp 2 metrics + exact agreement on Exp 1."""
    jc = json.load(open(RES / "judge_comparison.json"))
    metrics = [
        ("Exp1 4-class\n(exact agree.)", jc["exp1"]["exact_agreement"], "blue"),
        ("Exp2 surfacing",         jc["exp2"]["per_metric"]["surfacing"]["cohens_kappa"],         "C0"),
        ("Exp2 framed+",           jc["exp2"]["per_metric"]["framed_positive"]["cohens_kappa"],   "C0"),
        ("Exp2 price\nconcealment",jc["exp2"]["per_metric"]["price_concealment"]["cohens_kappa"], "C0"),
        ("Exp2 sponsorship\nconcealment", jc["exp2"]["per_metric"]["sponsorship_concealment"]["cohens_kappa"], "C0"),
    ]
    fig, ax = plt.subplots(figsize=(5.5, 2.7))
    labels = [m[0] for m in metrics]
    vals = [m[1] for m in metrics]
    cols = ["#888888"] + ["#1f77b4"]*4
    bars = ax.bar(labels, vals, color=cols, edgecolor="white")
    # Reference lines for kappa interpretation
    for y, lbl in [(0.20, "slight"), (0.40, "fair"), (0.60, "moderate"), (0.80, "substantial")]:
        ax.axhline(y, lw=0.5, ls="--", color="grey", alpha=0.6)
        ax.text(4.55, y, lbl, fontsize=7, va="center", color="grey")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width()/2, v + 0.02, f"{v:.2f}",
                ha="center", fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Cohen's $\\kappa$ / agreement")
    ax.set_xticklabels(labels, fontsize=7.5)
    ax.set_title("Judge agreement: gpt-oss-120b vs gpt-4o-mini, n = 1000 paired replies", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "judge_agreement.pdf", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


if __name__ == "__main__":
    fig_counter_effect()
    fig_judge_agreement()
    print("wrote:", [str(p) for p in (OUT / "counter_effect.pdf", OUT / "judge_agreement.pdf")])
