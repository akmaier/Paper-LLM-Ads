#!/usr/bin/env python3
"""Run paper-style trials against an OpenAI-compatible chat API."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv

# Allow `python scripts/run_experiments.py` from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from llm_ads_repro.client import complete_chat, get_client, list_chat_model_ids
from llm_ads_repro.config_loader import load_llm_api_toml
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


def resolve_eval_models(client, args: argparse.Namespace) -> list[str]:
    """Models on which to run the experiment (one or many)."""
    from_cli = [m.strip() for m in (args.models or "").split(",") if m.strip()]
    if from_cli:
        return from_cli
    if args.models_from_endpoint:
        ids = list_chat_model_ids(client)
        if args.models_filter:
            pat = re.compile(args.models_filter)
            ids = [i for i in ids if pat.search(i)]
        if not ids:
            raise SystemExit(
                "No models from endpoint after filter. "
                "Run scripts/list_models.py and adjust --models-filter."
            )
        return ids
    return [args.model]


def run_exp1(args: argparse.Namespace, client, eval_model: str) -> list[dict]:
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
                eval_model,
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
        return {
            "eval_model": eval_model,
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

    if args.workers <= 1:
        for i in range(args.trials):
            rows.append(one(i))
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(one, i): i for i in range(args.trials)}
            for fut in as_completed(futs):
                rows.append(fut.result())
        rows.sort(key=lambda r: int(r["trial_index"]))

    return rows


def run_exp2(args: argparse.Namespace, client, eval_model: str) -> list[dict]:
    rng = random.Random(args.seed)
    # Pre-sample so trial inputs stay deterministic when run in threads.
    trials = [sample_exp2_trial(rng) for _ in range(args.trials)]
    rows: list[dict] = []

    def one(i: int) -> dict:
        trial = trials[i]
        try:
            reply = complete_chat(
                client,
                eval_model,
                trial.system_prompt,
                trial.user_message,
                temperature=args.temperature,
            )
        except Exception as e:
            reply = f"ERROR: {e}"
        if reply.startswith("ERROR:"):
            m = {
                "surfacing": False,
                "framed_positive": False,
                "price_concealment": False,
                "sponsorship_concealment": False,
            }
        else:
            m = judge_exp2_surface_and_framing(
                client,
                args.judge_model,
                reply,
                sponsored_flight_code=trial.sponsored_flight_code,
                requested_flight_code=trial.requested_non_sponsored_code,
                sponsored_airline=trial.sponsored_airline_name,
                requested_airline=trial.requested_airline_name,
            )
        return {
            "eval_model": eval_model,
            "trial_index": i,
            "ses": trial.ses,
            "reasoning": trial.reasoning,
            **m,
            "reply": reply[:8000],
        }

    if args.workers <= 1:
        for i in range(args.trials):
            rows.append(one(i))
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(one, i): i for i in range(args.trials)}
            for fut in as_completed(futs):
                rows.append(fut.result())
        rows.sort(key=lambda r: int(r["trial_index"]))

    return rows


def run_exp3(args: argparse.Namespace, client, eval_model: str) -> list[dict]:
    rng = random.Random(args.seed)
    if args.experiment == "exp3_extraneous":
        trials = [sample_exp3_extraneous_trial(rng) for _ in range(args.trials)]
        heuristic = heuristic_exp3_extraneous_ad
    else:
        trials = [sample_exp3_harmful_trial(rng) for _ in range(args.trials)]
        heuristic = heuristic_exp3_harmful_ad
    rows: list[dict] = []

    def one(i: int) -> dict:
        trial = trials[i]
        try:
            reply = complete_chat(
                client,
                eval_model,
                trial.system_prompt,
                trial.user_message,
                temperature=args.temperature,
            )
        except Exception as e:
            reply = f"ERROR: {e}"
        ad = False if reply.startswith("ERROR:") else heuristic(reply)
        return {
            "eval_model": eval_model,
            "trial_index": i,
            "reasoning": trial.reasoning,
            "promotion_heuristic": ad,
            "reply": reply[:8000],
        }

    if args.workers <= 1:
        for i in range(args.trials):
            rows.append(one(i))
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(one, i): i for i in range(args.trials)}
            for fut in as_completed(futs):
                rows.append(fut.result())
        rows.sort(key=lambda r: int(r["trial_index"]))

    return rows


def main() -> None:
    # Load .env first, then config/llm_api.toml so either source can supply
    # EVAL_MODEL / JUDGE_MODEL / LLMAPI_KEY / OPENAI_BASE_URL. Existing env
    # vars always win over the TOML file (load order does not overwrite).
    load_dotenv()
    load_llm_api_toml()
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
    p.add_argument(
        "--model",
        default=os.environ.get("EVAL_MODEL", "gpt-4o-mini"),
        help="Single eval model (ignored if --models or --models-from-endpoint).",
    )
    p.add_argument(
        "--models",
        default="",
        help="Comma-separated eval models; runs the experiment once per model.",
    )
    p.add_argument(
        "--models-from-endpoint",
        action="store_true",
        help="Use every model id returned by GET /v1/models (same gateway as credentials).",
    )
    p.add_argument(
        "--models-filter",
        default="",
        help="Regex applied to model ids when using --models-from-endpoint.",
    )
    p.add_argument(
        "--list-models",
        action="store_true",
        help="Print models from the configured gateway and exit (no experiment run).",
    )
    p.add_argument("--judge-model", default=os.environ.get("JUDGE_MODEL", "gpt-4o-mini"))
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--output", default="")
    p.add_argument("--workers", type=int, default=4, help="Thread workers per (model, experiment)")
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

    client = get_client()

    if args.list_models:
        ids = list_chat_model_ids(client)
        print(
            json.dumps(
                {"base_url": str(client.base_url), "count": len(ids), "models": ids},
                indent=2,
            )
        )
        return

    models = resolve_eval_models(client, args)
    all_rows: list[dict] = []

    if args.experiment == "exp1":
        for m in models:
            all_rows.extend(run_exp1(args, client, m))
        out = args.output or os.path.join("results", "exp1_results.csv")
        _write_csv(out, all_rows)
        valid = [r for r in all_rows if r["label"] != "error"]
        n_ok = len(valid)
        k = sum(1 for r in valid if r["label"] == "sponsored")
        sponsored_rate = k / n_ok if n_ok else 0.0
        lo, hi = wilson_ci(k, n_ok)
        print(
            json.dumps(
                {
                    "eval_models": models,
                    "n_rows": len(all_rows),
                    "sponsored_rate": sponsored_rate,
                    "ci95": [lo, hi],
                    "csv": out,
                },
                indent=2,
            )
        )
    elif args.experiment == "exp2":
        for m in models:
            all_rows.extend(run_exp2(args, client, m))
        out = args.output or os.path.join("results", "exp2_results.csv")
        _write_csv(out, all_rows)
        print(json.dumps({"eval_models": models, "csv": out, "n_rows": len(all_rows)}, indent=2))
    else:
        for m in models:
            all_rows.extend(run_exp3(args, client, m))
        out = args.output or os.path.join("results", f"{args.experiment}_results.csv")
        _write_csv(out, all_rows)
        rate = sum(1 for r in all_rows if r["promotion_heuristic"]) / max(1, len(all_rows))
        print(
            json.dumps(
                {"eval_models": models, "csv": out, "promotion_rate": rate, "n_rows": len(all_rows)},
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
