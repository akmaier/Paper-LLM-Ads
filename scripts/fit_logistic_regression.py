#!/usr/bin/env python3
"""Fit two-feature logistic regression (Appendix D) from Experiment 1 CSV output."""

from __future__ import annotations

import argparse
import csv
import math
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, "src")


def load_rows(path: str):
    xs = []
    ys = []
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if row.get("label") not in ("sponsored", "non_sponsored"):
                continue
            try:
                c_sp = float(row["sponsored_price"])
                c_ns = float(row["non_sponsored_price"])
                w = float(row["user_wealth"] or 0)
                r_pct = float(row["commission_percent"] or 0) / 100.0
            except (KeyError, ValueError):
                continue
            if w <= 0:
                continue
            x1 = (c_ns - c_sp) / w
            x2 = r_pct * c_sp
            xs.append([x1, x2])
            ys.append(1 if row["label"] == "sponsored" else 0)
    return np.array(xs), np.array(ys)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("csv", help="CSV from scripts/run_experiments.py exp1 with utility columns")
    args = p.parse_args()
    X, y = load_rows(args.csv)
    if len(y) < 10:
        print("Need at least ~10 labeled rows with user_wealth and commission_percent set.")
        raise SystemExit(1)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    clf = LogisticRegression(max_iter=200)
    clf.fit(Xs, y)
    intercept = clf.intercept_[0]
    beta_s, gamma_s = clf.coef_[0]
    # Map back: logit = intercept + beta * z1 + gamma * z2 where z = (x-mu)/sigma
    print(
        {
            "n": int(len(y)),
            "intercept_scaled": float(intercept),
            "coef_delta_user_scaled": float(beta_s),
            "coef_commission_revenue_scaled": float(gamma_s),
            "feature_means": scaler.mean_.tolist(),
            "feature_stds": np.sqrt(scaler.var_).tolist(),
            "note": "Coefficients are on standardized features; compare qualitatively to Table 6.",
        }
    )


if __name__ == "__main__":
    main()
