#!/bin/zsh
# Rebuttal seed-robustness driver. Runs Exp1 baseline, Exp1 `compare` counter,
# and Exp3b harmful for ONE seed across the 9 paper open-weight models still
# hosted on NHR (IBM/granite-4.0-micro was retired from the gateway). Judge is
# gpt-oss-120b (OpenAI account not reachable at run time). Usage:
#   scripts/_rebuttal_seed_run.sh <seed> [workers]
SEED=$1
WORKERS=${2:-20}
MODELS="GaleneAI/Magistral-Small-2509-FP8-Dynamic,Microsoft/Phi-4-mini-instruct,Qwen/Qwen3.5-9B,Qwen/Qwen3.6-35B-A3B-FP8,Qwen3-VL-8B-Instruct,RedHatAI/Mistral-Small-3.2-24B-Instruct-2506-FP8,RedHatAI/gemma-3-27b-it-quantized.w4a16,google/gemma-4-E4B-it,gpt-oss-120b"
cd /Users/maier/Documents/code/Paper-LLM-Ads
. .venv/bin/activate
mkdir -p results/rebuttal
export PYTHONPATH=src

echo "[seed $SEED] exp1 baseline starting $(date +%T)"
python3 scripts/run_experiments.py exp1 --models "$MODELS" --trials 100 \
  --workers $WORKERS --judge-model gpt-oss-120b --seed $SEED \
  --output results/rebuttal/exp1_seed${SEED}.csv 2>&1 | grep -E 'sponsored_rate|n_rows'

echo "[seed $SEED] exp1 compare starting $(date +%T)"
python3 scripts/run_experiments.py exp1 --models "$MODELS" --trials 100 \
  --workers $WORKERS --judge-model gpt-oss-120b --seed $SEED --user-counter compare \
  --output results/rebuttal/exp1_compare_seed${SEED}.csv 2>&1 | grep -E 'sponsored_rate|n_rows'

echo "[seed $SEED] exp3_harmful starting $(date +%T)"
python3 scripts/run_experiments.py exp3_harmful --models "$MODELS" --trials 100 \
  --workers $WORKERS --seed $SEED \
  --output results/rebuttal/exp3_harmful_seed${SEED}.csv 2>&1 | grep -E 'promotion_rate|n_rows'

echo "[seed $SEED] DONE $(date +%T)"
