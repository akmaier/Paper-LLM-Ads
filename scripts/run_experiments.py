#!/usr/bin/env python3
"""Run paper-style trials against an OpenAI-compatible chat API."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict

from dotenv import load_dotenv

# Allow `python scripts/run_experiments.py` from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from llm_ads_repro.client import complete_chat, get_client
from llm_ads_repro.judges import (
    heuristic_exp3_extraneous_ad,
    heuristic_exp3_harmful_ad,
    judge_exp1_recommendation,
    judge_exp2_surface_and_framing,
)
from llm_ads_repro.stats_utils import wilson_ci
from llm_ads_repro.trial_sampling import (
    sample_exp1_trial,
    sample_exp2_trial,
    sample_exp3_extraneous_trial,
    sample_exp3_harmful_trial,
)


def _write_csv(path: str, rows: list[dict]) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def run_exp1(args: argparse.Namespace) -> None:
    load_dotenv()
    client = get_client()
    rng = random.Random(args.seed)
    rows: list[dict] = []

    def one(i: int) -> dict:
        trial = sample_exp1_trial(
            rng,
            commission_percent=args.commission_percent,
            user_wealth=args.user_wealth,
            steer=args.steer,
        )
        try:
            reply = complete_chat(
                client,
                args.model,
                trial.system_prompt,
                trial.user_message,
                temperature=args.temperature,
            )
        except Exception as e:
            reply = f"ERROR: {e}"
        label = "error"
        if not reply.startswith("ERROR:"):
            label = judge_exp1_recommendation(
                client,
                args.judge_model,
                reply,
                sponsored_flight_code=trial.sponsored_flight_code,
                non_sponsored_flight_code=trial.non_sponsored_flight_code,
                sponsored_airline=trial.sponsored_airline_name,
                non_sponsored_airline=trial.non_sponsored_airline_name,
            )
        row = {
            "trial_index": i,
            "ses": trial.ses,
            "reasoning": trial.reasoning,
            "system_variant": trial.system_variant,
            "steer": trial.steer,
            "commission_percent": trial.commission_percent or "",
            "user_wealth": trial.user_wealth or "",
            "sponsored_code": trial.sponsored_flight_code,
            "non_sponsored_code": trial.non_sponsored_flight_code,
            "sponsored_price": trial.sponsored_price,
            "non_sponsored_price": trial.non_sponsored_price,
            "label": label,
            "reply": reply[:8000],
        }
        return row

    if args.workers <= 1:
        for i in range(args.trials):
            rows.append(one(i))
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(one, i): i for i in range(args.trials)}
            for fut in as_completed(futs):
                rows.append(fut.result())
        rows.sort(key=lambda r: int(r["trial_index"]))

    out = args.output or os.path.join("results", "exp1_results.csv")
    _write_csv(out, rows)

    valid = [r for r in rows if r["label"] != "error"]
    n_ok = len(valid)
    k = sum(1 for r in valid if r["label"] == "sponsored")
    sponsored_rate = k / n_ok if n_ok else 0.0
    lo, hi = wilson_ci(k, n_ok)
    print(json.dumps({"n": len(rows), "sponsored_rate": sponsored_rate, "ci95": [lo, hi], "csv": out}, indent=2))


def run_exp2(args: argparse.Namespace) -> None:
    load_dotenv()
    client = get_client()
    rng = random.Random(args.seed)
    rows = []

    for i in range(args.trials):
        trial = sample_exp2_trial(rng)
        reply = complete_chat(
            client,
            args.model,
            trial.system_prompt,
            trial.user_message,
            temperature=args.temperature,
        )
        m = judge_exp2_surface_and_framing(
            client,
            args.judge_model,
            reply,
            sponsored_flight_code=trial.sponsored_flight_code,
            requested_flight_code=trial.requested_non_sponsored_code,
            sponsored_airline=trial.sponsored_airline_name,
            requested_airline=trial.requested_airline_name,
        )
        rows.append(
            {
                "trial_index": i,
                "ses": trial.ses,
                "reasoning": trial.reasoning,
                **m,
                "reply": reply[:8000],
            }
        )

    out = args.output or os.path.join("results", "exp2_results.csv")
    _write_csv(out, rows)
    print(json.dumps({"csv": out, "n": len(rows)}, indent=2))


def run_exp3(args: argparse.Namespace) -> None:
    load_dotenv()
    client = get_client()
    rng = random.Random(args.seed)
    rows = []

    for i in range(args.trials):
        if args.experiment == "exp3_extraneous":
            trial = sample_exp3_extraneous_trial(rng)
            reply = complete_chat(
                client,
                args.model,
                trial.system_prompt,
                trial.user_message,
                temperature=args.temperature,
            )
            ad = heuristic_exp3_extraneous_ad(reply)
        else:
            trial = sample_exp3_harmful_trial(rng)
            reply = complete_chat(
                client,
                args.model,
                trial.system_prompt,
                trial.user_message,
                temperature=args.temperature,
            )
            ad = heuristic_exp3_harmful_ad(reply)
        rows.append(
            {
                "trial_index": i,
                "reasoning": trial.reasoning,
                "promotion_heuristic": ad,
                "reply": reply[:8000],
            }
        )

    out = args.output or os.path.join("results", f"{args.experiment}_results.csv")
    _write_csv(out, rows)
    rate = sum(1 for r in rows if r["promotion_heuristic"]) / max(1, len(rows))
    print(json.dumps({"csv": out, "promotion_rate": rate}, indent=2))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "experiment",
        choices=[
            "exp1",
            "exp2",
            "exp3_extraneous",
            "exp3_harmful",
        ],
    )
    p.add_argument("--trials", type=int, default=10)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--model", default=os.environ.get("EVAL_MODEL", "gpt-4o-mini"))
    p.add_argument("--judge-model", default=os.environ.get("JUDGE_MODEL", "gpt-4o-mini"))
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--output", default="")
    p.add_argument("--workers", type=int, default=4, help="Thread workers for exp1 only")
    p.add_argument(
        "--commission-percent",
        type=int,
        default=None,
        choices=[1, 10, 20],
        help="Append corporate utility modulation (Experiment 1 extension).",
    )
    p.add_argument(
        "--user-wealth",
        type=float,
        default=None,
        help="Optional user wealth line for Experiment 1 utility extension.",
    )
    p.add_argument(
        "--steer",
        default="none",
        choices=["none", "customer", "website", "equal"],
        help="Experiment 1 steering (Appendix A.4).",
    )
    p.add_argument(
        "--print-sample",
        action="store_true",
        help="Print one sampled trial as JSON and exit (no API calls).",
    )
    args = p.parse_args()

    if args.print_sample:
        rng = random.Random(args.seed)
        if args.experiment == "exp1":
            t = sample_exp1_trial(
                rng,
                commission_percent=args.commission_percent,
                user_wealth=args.user_wealth,
                steer=args.steer,
            )
            print(json.dumps({"system": t.system_prompt, "user": t.user_message}, indent=2))
        elif args.experiment == "exp2":
            t = sample_exp2_trial(rng)
            print(json.dumps({"system": t.system_prompt, "user": t.user_message}, indent=2))
        elif args.experiment == "exp3_extraneous":
            t = sample_exp3_extraneous_trial(rng)
            print(json.dumps({"system": t.system_prompt, "user": t.user_message}, indent=2))
        else:
            t = sample_exp3_harmful_trial(rng)
            print(json.dumps({"system": t.system_prompt, "user": t.user_message}, indent=2))
        return

    if args.experiment == "exp1":
        run_exp1(args)
    elif args.experiment == "exp2":
        run_exp2(args)
    else:
        run_exp3(args)


if __name__ == "__main__":
    main()
