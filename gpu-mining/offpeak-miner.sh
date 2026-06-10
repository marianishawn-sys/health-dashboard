#!/usr/bin/env bash
# Off-peak GPU miner control for a single NVIDIA card (tested target: A40).
# Subcommands: prepare | run | cleanup | status
# Configuration comes from /etc/gpu-miner/gpu-miner.env (see gpu-miner.env.example).
set -euo pipefail

GPU_INDEX="${GPU_INDEX:-0}"
POWER_LIMIT_W="${POWER_LIMIT_W:-220}"          # A40 TDP is 300W; ~220W is the efficiency sweet spot
DEFAULT_POWER_LIMIT_W="${DEFAULT_POWER_LIMIT_W:-300}"
BUSY_UTIL_THRESHOLD="${BUSY_UTIL_THRESHOLD:-10}" # skip mining if GPU already >10% busy
MINER_CMD="${MINER_CMD:-}"

smi() { nvidia-smi -i "$GPU_INDEX" "$@"; }

case "${1:-}" in
  prepare)
    # refuse to mine if something else (AI job, rental) is using the card
    util=$(smi --query-gpu=utilization.gpu --format=csv,noheader,nounits)
    if (( util > BUSY_UTIL_THRESHOLD )); then
      echo "GPU $GPU_INDEX is ${util}% busy — not starting miner." >&2
      exit 1
    fi
    smi -pm 1                       # persistence mode
    smi -pl "$POWER_LIMIT_W"        # power cap for efficiency
    echo "GPU $GPU_INDEX prepared: power limit ${POWER_LIMIT_W}W."
    ;;

  run)
    if [[ -z "$MINER_CMD" ]]; then
      echo "MINER_CMD is not set — edit /etc/gpu-miner/gpu-miner.env" >&2
      exit 1
    fi
    echo "Starting miner on GPU $GPU_INDEX: $MINER_CMD"
    exec bash -c "$MINER_CMD"
    ;;

  cleanup)
    smi -pl "$DEFAULT_POWER_LIMIT_W" || true
    echo "GPU $GPU_INDEX power limit restored to ${DEFAULT_POWER_LIMIT_W}W."
    ;;

  status)
    smi --query-gpu=name,utilization.gpu,power.draw,power.limit,temperature.gpu \
        --format=csv
    systemctl is-active gpu-miner.service 2>/dev/null || true
    ;;

  *)
    echo "usage: $0 {prepare|run|cleanup|status}" >&2
    exit 64
    ;;
esac
