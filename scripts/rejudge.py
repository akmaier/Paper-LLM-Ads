#!/usr/bin/env python3
"""Retroactively re-judge existing per-trial CSVs without new eval calls.

Reads results/exp{1,2}*.csv (paths configurable), strips internal reasoning
from each saved reply (judges.strip_to_user_facing), and re-runs the judge.
The judge model is read from --judge-model (default `gpt-oss-120b` to match
the rest of this work) and uses whatever credentials the standard env / TOML
config supplies.

Why: judge labels in CSVs from earlier sweeps were produced with the
unstripped reply text, which mixed user-facing content with chain-of-thought
for some gateway models (Magistral, Qwen 3.5/3.6, etc.) and inflated/deflated
the binary metrics. This tool only updates the label columns; the per-trial
prompt randomization and the saved 'reply' field are preserved.

Usage:
    PYTHONPATH=src python3 scripts/rejudge.py \\
        --exp1 results/exp1_results.csv \\
        --exp2 results/exp2_results.csv \\
        --counters results/exp1_counter_*.csv \\
        --judge-model gpt-oss-120b \\
        --workers 6
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from llm_ads_repro.client import get_client
from llm_ads_repro.config_loader import force_openai_endpoint, load_llm_api_toml
from llm_ads_repro.judges import judge_exp1_recommendation, judge_exp2_surface_and_framing


def _rows(path: str) -> tuple[list[str], list[dict]]:
    with open(path, encoding="utf-8") as f:
        r = csv.DictReader(f)
        rows = list(r)
        return list(r.fieldnames or []), rows


def _save(path: str, fields: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def rejudge_exp1(client, judge_model: str, rows: list[dict], workers: int) -> int:
    """Re-label every row in-place. Returns count of changed rows."""

    def one(r: dict) -> tuple[dict, str]:
        reply = r.get("reply", "")
        if not reply or reply.startswith("ERROR:"):
            return r, r.get("label", "error")
        new = judge_exp1_recommendation(
            client, judge_model, reply,
            sponsored_flight_code=r.get("sponsored_code", ""),
            non_sponsored_flight_code=r.get("non_sponsored_code", ""),
            sponsored_airline=r.get("sponsored_code", "").split()[0] if r.get("sponsored_code") else "",
            non_sponsored_airline=r.get("non_sponsored_code", "").split()[0] if r.get("non_sponsored_code") else "",
        )
        return r, new

    changed = 0
    if workers <= 1:
        for r in rows:
            _, new = one(r)
            if new != r.get("label"):
                changed += 1
                r["label"] = new
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(one, r): r for r in rows}
            for fut in as_completed(futs):
                r, new = fut.result()
                if new != r.get("label"):
                    changed += 1
                    r["label"] = new
    return changed


def rejudge_exp2(client, judge_model: str, rows: list[dict], workers: int) -> int:
    """Re-label every row's four boolean metrics in-place. Returns count
    of rows whose at least one metric changed."""

    def one(r: dict) -> tuple[dict, dict]:
        reply = r.get("reply", "")
        if not reply or reply.startswith("ERROR:"):
            return r, {
                "surfacing": False,
                "framed_positive": False,
                "price_concealment": False,
                "sponsorship_concealment": False,
            }
        m = judge_exp2_surface_and_framing(
            client, judge_model, reply,
            sponsored_flight_code=r.get("sponsored_code", ""),
            requested_flight_code=r.get("requested_non_sponsored_code", ""),
            sponsored_airline="", requested_airline="",
        )
        return r, m

    changed = 0
    keys = ("surfacing", "framed_positive", "price_concealment", "sponsorship_concealment")
    if workers <= 1:
        for r in rows:
            _, m = one(r)
            old = {k: str(r.get(k, "")).strip().lower() in ("true", "1", "yes") for k in keys}
            if any(old[k] != m[k] for k in keys):
                changed += 1
            for k in keys:
                r[k] = m[k]
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(one, r): r for r in rows}
            for fut in as_completed(futs):
                r, m = fut.result()
                old = {k: str(r.get(k, "")).strip().lower() in ("true","1","yes") for k in keys}
                if any(old[k] != m[k] for k in keys):
                    changed += 1
                for k in keys:
                    r[k] = m[k]
    return changed


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--exp1", default="results/exp1_results.csv")
    p.add_argument("--exp2", default="results/exp2_results.csv")
    p.add_argument(
        "--counters",
        nargs="*",
        default=[
            "results/exp1_counter_ignore.csv",
            "results/exp1_counter_rule.csv",
            "results/exp1_counter_reframe.csv",
            "results/exp1_counter_compare.csv",
        ],
    )
    p.add_argument("--judge-model", default=os.environ.get("JUDGE_MODEL", "gpt-oss-120b"))
    p.add_argument("--workers", type=int, default=6)
    p.add_argument(
        "--use-openai",
        action="store_true",
        help=(
            "Talk to OpenAI's API directly (pops OPENAI_BASE_URL). Pair with "
            "--judge-model gpt-4o-mini for paper-comparable Exp 2 calibration."
        ),
    )
    args = p.parse_args()

    load_dotenv()
    load_llm_api_toml()
    if args.use_openai:
        force_openai_endpoint()
    client = get_client()

    targets_exp1 = [args.exp1, *args.counters]
    for path in targets_exp1:
        if not os.path.isfile(path):
            print(f"skip (missing): {path}")
            continue
        fields, rows = _rows(path)
        n_changed = rejudge_exp1(client, args.judge_model, rows, args.workers)
        _save(path, fields, rows)
        print(f"{path}: rejudged {len(rows)} rows, {n_changed} labels changed")

    if os.path.isfile(args.exp2):
        fields, rows = _rows(args.exp2)
        n_changed = rejudge_exp2(client, args.judge_model, rows, args.workers)
        _save(args.exp2, fields, rows)
        print(f"{args.exp2}: rejudged {len(rows)} rows, {n_changed} rows changed")


if __name__ == "__main__":
    main()
