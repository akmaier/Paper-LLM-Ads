#!/usr/bin/env python3
"""Print every headline number reported in the paper, derived from the
gpt-4o-judged labels. Open-source rows use the *.gpt-4o.csv siblings;
OpenAI rows use the (re-judged) bare *_openai.csv files.

This is a one-off auxiliary; the canonical analyses are
figures_of_merit.py + summarize_results.py.
"""
from __future__ import annotations
import csv, glob, math, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from llm_ads_repro.stats_utils import wilson_ci

ROOT = os.path.join(os.path.dirname(__file__), "..")
RES = os.path.join(ROOT, "results")


def boolish(v):
    return str(v).strip().lower() in ("true", "1", "yes")


def rate(path, hit_fn=lambda r: r["label"] == "sponsored", filter_fn=lambda r: True):
    rows = [r for r in csv.DictReader(open(path)) if filter_fn(r)]
    n = len(rows); k = sum(1 for r in rows if hit_fn(r))
    lo, hi = wilson_ci(k, n) if n else (0.0, 0.0)
    return n, k, k / n if n else 0.0, lo, hi


def per_model(path, hit_fn=lambda r: r["label"] == "sponsored"):
    out = {}
    for r in csv.DictReader(open(path)):
        m = r["eval_model"]
        d = out.setdefault(m, {"n": 0, "k": 0})
        d["n"] += 1
        if hit_fn(r): d["k"] += 1
    return out


# === Exp 1 sponsored, per-model + aggregates, under gpt-4o judge ============
print("\n== Exp 1 sponsored rate, gpt-4o judge ==")
os_csv = f"{RES}/exp1_results.gpt-4o.csv"          # open-source, 1000 rows
oa_csv = f"{RES}/exp1_results_openai.csv"          # OpenAI, 200 rows
n,k,p,_,_ = rate(os_csv); print(f"  open-source pool  k={k}/{n}  rate={p:.3f}")
n,k,p,_,_ = rate(oa_csv); print(f"  OpenAI pool       k={k}/{n}  rate={p:.3f}")

print("  per model (open-source):")
for m, d in sorted(per_model(os_csv).items()):
    p = d["k"]/d["n"] if d["n"] else 0
    print(f"    {m:55s}  {d['k']:>3d}/{d['n']}  {p:.2f}")
print("  per model (OpenAI):")
for m, d in sorted(per_model(oa_csv).items()):
    p = d["k"]/d["n"] if d["n"] else 0
    print(f"    {m:55s}  {d['k']:>3d}/{d['n']}  {p:.2f}")

# === Exp 2 marginal + conditional-on-surfacing, under gpt-4o ==============
print("\n== Exp 2 (gpt-4o judge) ==")
for tag, path in [("open-source", f"{RES}/exp2_results.gpt-4o.csv"),
                  ("OpenAI",      f"{RES}/exp2_results_openai.csv")]:
    rows = list(csv.DictReader(open(path)))
    n = len(rows)
    keys = ("surfacing","framed_positive","price_concealment","sponsorship_concealment")
    marg = {k: sum(1 for r in rows if boolish(r.get(k)))/n for k in keys}
    surf_rows = [r for r in rows if boolish(r.get("surfacing"))]
    nc = len(surf_rows)
    cond = {k: (sum(1 for r in surf_rows if boolish(r.get(k)))/nc if nc else 0.0)
            for k in keys if k != "surfacing"}
    print(f"  [{tag}] marginal: " + ", ".join(f"{k}={v:.2f}" for k,v in marg.items()))
    print(f"             cond|surf (n_surf={nc}): " + ", ".join(f"{k}={v:.2f}" for k,v in cond.items()))

# === Counter aggregate, gpt-4o ============================================
print("\n== Counter aggregate sponsored rate, gpt-4o judge ==")
for c in ("ignore","rule","reframe","compare"):
    os_p = f"{RES}/exp1_counter_{c}.gpt-4o.csv"
    oa_p = f"{RES}/exp1_counter_{c}_openai.csv"
    if os.path.isfile(os_p):
        n,k,p,_,_ = rate(os_p)
        print(f"  {c:>10s}  open-source: {k}/{n}={p:.3f}", end="  ")
    if os.path.isfile(oa_p):
        n,k,p,_,_ = rate(oa_p)
        print(f"OpenAI: {k}/{n}={p:.3f}")
    else:
        print()

# Per-counter, per-model
print("\n== Counter per-model, gpt-4o ==")
for c in ("ignore","rule","reframe","compare"):
    os_p = f"{RES}/exp1_counter_{c}.gpt-4o.csv"
    oa_p = f"{RES}/exp1_counter_{c}_openai.csv"
    if not os.path.isfile(os_p): continue
    pm_os = per_model(os_p); pm_oa = per_model(oa_p) if os.path.isfile(oa_p) else {}
    print(f"  -- {c} --")
    for m, d in sorted(pm_os.items()):
        print(f"    {m:55s}  {d['k']:>3d}/{d['n']}  {d['k']/d['n']:.2f}")
    for m, d in sorted(pm_oa.items()):
        print(f"    {m:55s}  {d['k']:>3d}/{d['n']}  {d['k']/d['n']:.2f}")

# === Commission/wealth grid + logistic regression, gpt-4o ================
print("\n== Commission/wealth grid (gpt-3.5-turbo), gpt-4o judge ==")
try:
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    X = []; y = []
    for path in sorted(glob.glob(f"{RES}/exp1_commission_*_wealth_*_openai.csv")):
        m = re.search(r"commission_(\d+)_wealth_(\d+)_openai", path)
        cp, w = int(m.group(1)), int(m.group(2))
        n,k,p,_,_ = rate(path)
        print(f"  cp={cp:>2d}% wealth=${w:>7d}: {k}/{n}={p:.2f}")
        for r in csv.DictReader(open(path)):
            if r["label"] == "error": continue
            y.append(1 if r["label"]=="sponsored" else 0)
            X.append([cp, math.log10(w)])
    X = np.array(X); y = np.array(y)
    Xs = (X - X.mean(0)) / X.std(0)
    clf = LogisticRegression(C=1e6).fit(Xs, y)
    print(f"  --> n={len(y)}  intercept={clf.intercept_[0]:+.3f}  "
          f"std_coef_commission={clf.coef_[0,0]:+.3f}  "
          f"std_coef_log_wealth={clf.coef_[0,1]:+.3f}")
except Exception as e:
    print(f"  (regression skipped: {e})")

# === Steering, gpt-4o judge ==============================================
print("\n== Steering on gpt-4o (eval), under gpt-4o (judge) ==")
for s in ("customer","equal","website"):
    p_ = f"{RES}/exp1_steer_{s}_openai.csv"
    if os.path.isfile(p_):
        n,k,p,_,_ = rate(p_)
        print(f"  steer={s:>10s}: {k}/{n}={p:.2f}")
