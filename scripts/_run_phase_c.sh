#!/bin/bash
# Phase C driver: §4.3 commission/wealth grid + §4.5 steering.
# Launched manually from the repo root once Phase B is finished, so we
# do not overwhelm OpenAI rate limits with too many concurrent runs.
#
# Outputs:
#   results/exp1_commission_<pct>_wealth_<w>_openai.csv  (12 files)
#   results/exp1_steer_<mode>_openai.csv                  (3 files)
#
# Total cost rough-out: ~$8 with gpt-3.5-turbo for the grid + ~$5 with
# gpt-4o for steering, plus gpt-4o-mini judge.

set -e
cd "$(dirname "$0")/.."

mkdir -p logs results

# §4.3 commission/wealth grid on gpt-3.5-turbo (cheap; in paper Table 2)
for cp in 1 10 20; do
  for w in 500 5000 50000 200000; do
    out="results/exp1_commission_${cp}_wealth_${w}_openai.csv"
    log="logs/grid_c${cp}_w${w}.log"
    if [ -s "$out" ]; then echo "skip $out"; continue; fi
    PYTHONPATH=src .venv/bin/python scripts/run_experiments.py exp1 \
      --use-openai --models-from-endpoint --models-filter '^gpt-3\.5-turbo$' \
      --judge-model gpt-4o-mini \
      --commission-percent "$cp" --user-wealth "$w" \
      --trials 100 --workers 4 \
      --output "$out" \
      > "$log" 2>&1
    echo "done: $out (cp=$cp, wealth=$w)"
  done
done

# §4.5 steering on gpt-4o (paper Figure 2)
for s in customer equal website; do
  out="results/exp1_steer_${s}_openai.csv"
  log="logs/steer_${s}.log"
  if [ -s "$out" ]; then echo "skip $out"; continue; fi
  PYTHONPATH=src .venv/bin/python scripts/run_experiments.py exp1 \
    --use-openai --models-from-endpoint --models-filter '^gpt-4o$' \
    --judge-model gpt-4o-mini \
    --steer "$s" \
    --trials 100 --workers 4 \
    --output "$out" \
    > "$log" 2>&1
  echo "done: $out (steer=$s)"
done

echo "Phase C complete."
