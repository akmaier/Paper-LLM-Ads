# Reproducing: “Ads in AI Chatbots?” (arXiv:2604.08525)

This repository contains a **faithful prompt-and-protocol reproduction** of the evaluation suite in:

> **Ads in AI Chatbots? An Analysis of How Large Language Models Navigate Conflicts of Interest**  
> Addison J. Wu, Ryan Liu, Shuyue Stella Li, Yulia Tsvetkov, Thomas L. Griffiths  
> [arXiv:2604.08525](https://arxiv.org/abs/2604.08525) — PDF: [https://arxiv.org/pdf/2604.08525](https://arxiv.org/pdf/2604.08525)

The paper studies how LLMs behave when a **travel-booking assistant** is softly incentivized to favor **sponsored airlines** (more expensive) over cheaper non-sponsored flights, plus follow-on scenarios (extraneous recommendations, sponsored study tools, harmful financial products).

## What was downloaded

The PDF was fetched for reference during implementation (not committed):

```bash
curl -L -o paper.pdf "https://arxiv.org/pdf/2604.08525"
```

## What this codebase reproduces

| Paper | Section | This repo |
|--------|---------|-----------|
| Experiment 1 | §4.1, App. A.1–A.3, A.6.1 | `sample_exp1_trial` — two flights (sponsored vs cheaper), SES personas, direct vs CoT add-ons, three system-prompt variants; optional commission sentence (§4.3), optional wealth line, steering prompts (§4.5 / App. A.4) |
| Experiment 2 | §5.1, App. A.3 | `sample_exp2_trial` — user asks to book a **specific** non-sponsored airline; formatted response (App. A.6.2); LLM-as-judge for surfacing / framing / concealment-style metrics |
| Experiment 3a | §6.1–6.2, App. A.5 | `sample_exp3_extraneous_trial` — MATH-style problem + Chegg / Brainly / Photomath sponsorship prompt; **keyword heuristic** for “recommended sponsor” (paper used qualitative rates) |
| Experiment 3b | §6.3–6.4, App. A.5 | `sample_exp3_harmful_trial` — financial distress vignettes + payday-lender sponsors; **keyword heuristic** for harmful promotion |

**Differences from the paper (explicit):**

- **Models:** The authors ran **23 proprietary and open models** (App. B). Here you supply **any OpenAI-compatible endpoint** via `OPENAI_API_KEY` / `OPENAI_BASE_URL` and `--model`.
- **Trial count:** The paper uses **100 trials** per (model × reasoning × SES) cell. Use `--trials 100` (or larger) to match; default in the script is small for cost control.
- **Judgments:** Experiment 1 primary outcome is **which flight is recommended**. We use a **second LLM judge** (`--judge-model`, default `gpt-4o-mini`) with a JSON label rubric. The paper does not fully specify automated parsing; this is a practical reproducibility choice.
- **Experiment 3 metrics:** The paper reports human-interpreted “advertisement rates”; we use **transparent string heuristics** (documented in `src/llm_ads_repro/judges.py`) so runs are cheap and repeatable. Swap in your own judge if you need closer alignment to their manual coding.
- **MATH dataset:** The paper draws items from the full **MATH** benchmark. This repo ships a **small fixed pool** of algebra-style items so the pipeline runs without extra downloads; replace `MATH_SAMPLE_PROBLEMS` in `constants.py` for stricter alignment.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional: create `.env` with:

```bash
OPENAI_API_KEY=sk-...
# Optional: Azure, OpenRouter, local vLLM, etc.
# OPENAI_BASE_URL=https://...
EVAL_MODEL=gpt-4o-mini
JUDGE_MODEL=gpt-4o-mini
```

## Inspect prompts (no API calls)

```bash
PYTHONPATH=src python3 scripts/run_experiments.py exp1 --print-sample --seed 1
PYTHONPATH=src python3 scripts/run_experiments.py exp2 --print-sample
PYTHONPATH=src python3 scripts/run_experiments.py exp3_extraneous --print-sample
PYTHONPATH=src python3 scripts/run_experiments.py exp3_harmful --print-sample
```

## Run experiments

**Experiment 1 (sponsored vs cheaper recommendation):**

```bash
PYTHONPATH=src python3 scripts/run_experiments.py exp1 \
  --trials 100 \
  --model gpt-4o-mini \
  --judge-model gpt-4o-mini \
  --workers 8
```

**Extension — commission + wealth (logistic features as in §4.3 / App. D):**

```bash
PYTHONPATH=src python3 scripts/run_experiments.py exp1 \
  --trials 200 \
  --commission-percent 10 \
  --user-wealth 50000
```

Then fit a standardized two-feature logistic model (illustrative; compare qualitatively to Table 6):

```bash
python3 scripts/fit_logistic_regression.py results/exp1_results.csv
```

**Steering (App. A.4):**

```bash
PYTHONPATH=src python3 scripts/run_experiments.py exp1 --trials 50 --steer customer
```

**Experiment 2 (extraneous sponsored surfacing):**

```bash
PYTHONPATH=src python3 scripts/run_experiments.py exp2 --trials 50
```

**Experiment 3:**

```bash
PYTHONPATH=src python3 scripts/run_experiments.py exp3_extraneous --trials 20
PYTHONPATH=src python3 scripts/run_experiments.py exp3_harmful --trials 20
```

CSV outputs default to `results/`.

## Ethics and safety

Experiment **3b** uses prompts modeled on **predatory lending** as in the paper’s harm analysis. Use only for **aligned research** (measuring refusal vs promotion), not for end-user deployment. The heuristics here are **not** safety evaluations on their own.

## Tests

```bash
pip install pytest
PYTHONPATH=src python3 -m pytest tests/ -q
```

## Layout

- `src/llm_ads_repro/constants.py` — Appendix A stimuli (flights, personas, system prompts, add-ons).
- `src/llm_ads_repro/trial_sampling.py` — Randomization protocol (sponsor set, prices, personas).
- `src/llm_ads_repro/client.py` — OpenAI-compatible chat completion.
- `src/llm_ads_repro/judges.py` — Judging and Experiment 3 heuristics.
- `scripts/run_experiments.py` — CLI runner and CSV export.
- `scripts/fit_logistic_regression.py` — Optional logistic fit on CSV.

## Citation

```bibtex
@article{wu2026ads,
  title={Ads in {AI} Chatbots? An Analysis of How Large Language Models Navigate Conflicts of Interest},
  author={Wu, Addison J. and Liu, Ryan and Li, Shuyue Stella and Tsvetkov, Yulia and Griffiths, Thomas L.},
  journal={arXiv preprint arXiv:2604.08525},
  year={2026}
}
```
