#!/usr/bin/env python3
"""Push the per-trial CSVs + derived JSON to akmaier/LLM-Ads on Hugging Face.

Reads the data files from `results/` and uploads them under a flat layout
plus a `README.md` data card. Requires either a token in the standard
HuggingFace cache (`huggingface-cli login`), an `HF_TOKEN` env var, or
`--token` on the command line.

Layout on the Hub mirrors the layout in this repo:

    results/
        exp1_results.csv
        exp1_results.gpt-4o.csv
        exp1_results.gpt-4o-mini.csv
        ...
        figures_of_merit.json
        judge_comparison.json

The data card (README.md at the root of the HF repo) documents what
each file contains and links back to the paper and the source repo.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ID = "akmaier/LLM-Ads"
REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results"

DATA_CARD = """\
---
license: cc-by-4.0
language:
  - en
size_categories:
  - 10K<n<100K
task_categories:
  - text-classification
tags:
  - llm-evaluation
  - llm-as-judge
  - advertising
  - reproducibility
pretty_name: LLM-Ads — Sponsored-recommendation evaluation traces
---

# LLM-Ads — Sponsored-recommendation evaluation traces

Per-trial responses and labels from the experiments in
*Just Ask for a Table: A Thirty-Token User Prompt Defeats Sponsored
Recommendations in Twelve LLMs*
(arXiv:[2605.12772](https://arxiv.org/html/2605.12772v1)).

The data set reproduces and extends the evaluation of Wu et al.\\ 2026
(arXiv:[2604.08525](https://arxiv.org/abs/2604.08525)) on a twelve-model
pool (ten open-source chat models served through an OpenAI-compatible
API endpoint plus the two paper-overlap OpenAI models
`gpt-3.5-turbo` and `gpt-4o`).

## Layout

Every CSV stores one trial per row, with columns:

| column | description |
|---|---|
| `eval_model` | the evaluated LLM id |
| `trial_index` | 0-indexed trial number within `(eval_model, condition)` |
| `ses` | low/high socio-economic-status persona |
| `reasoning` | direct / cot |
| `system_variant` | which of the three Appendix A.2 system-prompt variants is used |
| `steer` | none / customer / equal / website (Experiment 1 only) |
| `user_counter` | none / ignore / rule / reframe / compare (Experiment 1 only) |
| `commission_percent`, `user_wealth` | Experiment 1 §4.3 extension |
| `sponsored_code`, `non_sponsored_code` | flight identifiers |
| `sponsored_price`, `non_sponsored_price` | dollar amounts |
| `label` | classification by the LLM judge (Exp 1: sponsored / non_sponsored / unclear / refusal / error) |
| `surfacing`, `framed_positive`, `price_concealment`, `sponsorship_concealment` | binary labels (Exp 2 only) |
| `promotion_heuristic` | True / False keyword-heuristic flag (Exp 3 only) |
| `reply` | the model's reply text (capped at 8000 chars) |

File-name conventions:

- `exp1_results*.csv` — Experiment 1 (sponsored vs. cheaper recommendation).
- `exp2_results*.csv` — Experiment 2 (user requests a non-sponsored airline).
- `exp3_extraneous_results*.csv` — Experiment 3a (study-tool ad on a math problem).
- `exp3_harmful_results*.csv` — Experiment 3b (payday-lender ad to a financially distressed user).
- `exp1_counter_<ignore|rule|reframe|compare>*.csv` — RQ3 user-side counter-prompts.
- `exp1_commission_<pct>_wealth_<usd>*.csv` — §4.3 commission/wealth grid (gpt-3.5-turbo, 12 cells × 100 trials).
- `exp1_steer_<customer|equal|website>*.csv` — §4.5 steering grid (gpt-4o).
- `*_openai.csv` — runs against OpenAI API (`gpt-3.5-turbo`, `gpt-4o`).
- `*.gpt-4o.csv` / `*.gpt-4o-mini.csv` — same per-trial replies, re-judged with `gpt-4o` / `gpt-4o-mini`. Bare CSVs carry `gpt-oss-120b` labels (open-source pool) or `gpt-4o` labels (OpenAI pool, after the in-place re-judge).

Derived files:

- `figures_of_merit.json`, `figures_of_merit_openai.json` — per-model
  rates with Wilson 95 % CIs, plus per-SES, per-reasoning, per-system-
  variant, per-steer, per-user-counter breakdowns and the
  conditional-on-surfacing rates for Exp 2 (paper Tables 3 & 4).
- `judge_comparison.json` — three-judge ablation
  (`gpt-oss-120b`, `gpt-4o-mini`, `gpt-4o`).
- `counter_comparison.json` — open-source counter sweep summary.
- `summary.json` — aggregate per-model rates.
- `logistic_regression_gpt-3.5-turbo.json` — fitted intercept and
  standardised coefficients for the commission/wealth grid.

## How to reproduce the paper's tables from this data

```python
from datasets import load_dataset
ds = load_dataset("akmaier/LLM-Ads", data_files="results/exp1_results.gpt-4o.csv")
```

The source code that produced these CSVs lives at
<https://github.com/akmaier/Paper-LLM-Ads>; the same scripts also
compute the derived JSON summaries:

```
python scripts/summarize_results.py
python scripts/figures_of_merit.py
python scripts/compare_judges.py
```

## License

Released under CC-BY-4.0. If you build on this data set, please cite
the paper:

```bibtex
@article{Maier26-LLM-Ads,
  title  = {Just Ask for a Table: A Thirty-Token User Prompt Defeats Sponsored Recommendations in Twelve LLMs},
  author = {Maier, Andreas and Sopa, Jeta and {\\c{S}}ahin, G{\\\"o}zde G{\\\"u}l and P{\\'e}rez-Toro, Paula and Bayer, Siming},
  journal = {arXiv preprint arXiv:2605.12772},
  year   = {2026}
}
```
"""


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-id", default=REPO_ID)
    p.add_argument("--token", default=None, help="HF write token (else use env / login)")
    p.add_argument("--dry-run", action="store_true", help="list files only; do not upload")
    args = p.parse_args()

    try:
        from huggingface_hub import HfApi, create_repo
    except ImportError:
        print("error: huggingface_hub not installed (.venv/bin/pip install huggingface_hub)")
        sys.exit(2)

    token = args.token or os.environ.get("HF_TOKEN") or None

    # Pick up the data files we want to ship
    files = sorted(RESULTS_DIR.glob("*.csv")) + sorted(RESULTS_DIR.glob("*.json"))
    if not files:
        print(f"error: no CSV/JSON files found in {RESULTS_DIR}")
        sys.exit(1)

    print(f"will upload {len(files)} data files to {args.repo_id}:")
    for f in files:
        print(f"  results/{f.name}  ({f.stat().st_size:,} bytes)")
    print(f"plus a generated README.md data card")
    if args.dry_run:
        print("dry-run: nothing pushed.")
        return

    api = HfApi(token=token)
    create_repo(args.repo_id, repo_type="dataset", exist_ok=True, token=token)

    # Data card first
    card_path = "/tmp/_llm_ads_README.md"
    Path(card_path).write_text(DATA_CARD)
    api.upload_file(
        path_or_fileobj=card_path, path_in_repo="README.md",
        repo_id=args.repo_id, repo_type="dataset", token=token,
        commit_message="docs: data card",
    )

    # All the CSV and JSON files under results/
    for f in files:
        api.upload_file(
            path_or_fileobj=str(f), path_in_repo=f"results/{f.name}",
            repo_id=args.repo_id, repo_type="dataset", token=token,
            commit_message=f"add {f.name}",
        )
    print(f"\ndone. https://huggingface.co/datasets/{args.repo_id}")


if __name__ == "__main__":
    main()
