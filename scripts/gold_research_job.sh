#!/usr/bin/env bash
# Detached local experiments; the Python worker validates/resumes checkpoints.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${GOLD_RESEARCH_PYTHON:-/tmp/gold-backtest-venv/bin/python}"
OUTPUT_DIR="${GOLD_RESEARCH_OUTPUT:-${ROOT_DIR}/analysis_outputs/gold_research_v1}"
SESSION_NAME="gold-research-v1"
case "${1:-status}" in
  start)
    mkdir -p "${OUTPUT_DIR}"
    if tmux -L gold-research has-session -t "${SESSION_NAME}" 2>/dev/null; then
      echo "Already running: ${SESSION_NAME}"
      exit 0
    fi
    printf -v COMMAND '%q ' "${PYTHON_BIN}" "${ROOT_DIR}/scripts/run_gold_research.py" --out-dir "${OUTPUT_DIR}" --workers 4
    printf -v LOGFILE '%q' "${OUTPUT_DIR}/worker.log"
    tmux -L gold-research new-session -d -s "${SESSION_NAME}" -c "${ROOT_DIR}" "exec ${COMMAND} >> ${LOGFILE} 2>&1"
    echo "Started/resumed ${SESSION_NAME}; log: ${OUTPUT_DIR}/worker.log"
    ;;
  status)
    if tmux -L gold-research has-session -t "${SESSION_NAME}" 2>/dev/null; then
      echo "Worker tmux session is running"
    else
      echo "Worker tmux session is not running"
    fi
    if [[ -f "${OUTPUT_DIR}/status.json" ]]; then cat "${OUTPUT_DIR}/status.json"; fi
    ;;
  *) echo "Usage: bash scripts/gold_research_job.sh start|status"; exit 2 ;;
esac
