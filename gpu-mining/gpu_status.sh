#!/usr/bin/env bash
# Emit GPU status JSON for the SAVANT dashboard's GPU panel.
# Wire to n8n: Webhook (POST /webhook/savant-gpu) -> Execute Command
# (this script) -> Respond to Webhook (stdout, application/json).
set -euo pipefail

GPU_INDEX="${GPU_INDEX:-0}"
JARVIS_UTIL_THRESHOLD="${JARVIS_UTIL_THRESHOLD:-10}"

q=$(nvidia-smi -i "$GPU_INDEX" \
  --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,power.limit \
  --format=csv,noheader,nounits)
IFS=',' read -r name util memu memt temp pow plim <<<"$q"
trim() { local s="$1"; s="${s#"${s%%[![:space:]]*}"}"; echo "${s%"${s##*[![:space:]]}"}"; }
name=$(trim "$name"); util=$(trim "$util"); memu=$(trim "$memu"); memt=$(trim "$memt")
temp=$(trim "$temp"); pow=$(trim "$pow"); plim=$(trim "$plim")

# workload: miner if the off-peak miner service is running, else busy GPU
# means JARVIS (inference/training), else idle
wl=idle
if systemctl is-active --quiet gpu-miner.service 2>/dev/null; then
  wl=miner
elif [[ "${util%%.*}" -gt "$JARVIS_UTIL_THRESHOLD" ]]; then
  wl=jarvis
fi

printf '{"generated":"%s","workload":"%s","gpus":[{"index":%s,"name":"%s","util":%s,"memUsed":%s,"memTotal":%s,"temp":%s,"power":%s,"powerLimit":%s}]}\n' \
  "$(date -u +%FT%TZ)" "$wl" "$GPU_INDEX" "$name" \
  "${util:-0}" "${memu:-0}" "${memt:-0}" "${temp:-null}" "${pow:-0}" "${plim:-0}"
