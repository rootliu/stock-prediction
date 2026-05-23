#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
OUTPUT_DIR="${1:-${GOLD_DIRECT_OUTPUT_DIR:-}}"
TARGET_END="${2:-${GOLD_TARGET_END:-}}"

if [[ -z "${OUTPUT_DIR}" ]]; then
  echo "Usage: $0 <output-dir> [target-end]"
  echo "Or set GOLD_DIRECT_OUTPUT_DIR and optional GOLD_TARGET_END."
  exit 1
fi

# Auto-compute target-end: 3rd future trading day
if [[ -z "${TARGET_END}" ]]; then
  TARGET_END="$("${PYTHON_BIN}" - <<'PY'
import pandas as pd
from datetime import date, timedelta
try:
    import akshare as ak
    today = pd.Timestamp(date.today()).normalize()
    calendar = ak.tool_trade_date_hist_sina()
    trade_dates = pd.to_datetime(calendar["trade_date"]).dt.normalize()
    future = trade_dates[trade_dates > today]
    if len(future) >= 3:
        print(pd.Timestamp(future.iloc[2]).strftime("%Y-%m-%d"))
    elif len(future) > 0:
        print(pd.Timestamp(future.iloc[-1]).strftime("%Y-%m-%d"))
    else:
        raise RuntimeError("empty future trade calendar")
except Exception:
    d = date.today()
    count = 0
    while count < 3:
        d += timedelta(days=1)
        if d.weekday() < 5:
            count += 1
    print(d.isoformat())
PY
)"
fi

mkdir -p "${OUTPUT_DIR}"

echo "Target end: ${TARGET_END}"
echo "Output dir: ${OUTPUT_DIR}"

# v3 direct + guards (per AI-C 2026-05-23 directional guardrails work)
# Outputs: report.txt (full log) + gold_direct_scenario_*.{md,png,csv,json}
MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/mpl-stock}" \
PYTHONUNBUFFERED=1 \
"${PYTHON_BIN}" "${ROOT_DIR}/run_gold_analysis.py" \
  --forecast-mode direct \
  --skip-backtest \
  --target-end "${TARGET_END}" \
  --report-dir "${OUTPUT_DIR}" \
  2>&1 | tee "${OUTPUT_DIR}/report.txt"

# Locate the latest scenario bundle (run_gold_analysis stamps it with target-end)
LATEST_MD="$(/bin/ls -1t "${OUTPUT_DIR}"/gold_direct_scenario_*.md 2>/dev/null | head -n 1)"
if [[ -n "${LATEST_MD}" ]]; then
  LATEST_BASE="${LATEST_MD%.md}"
  cp -f "${LATEST_BASE}.md"   "${OUTPUT_DIR}/report.md"   2>/dev/null || true
  cp -f "${LATEST_BASE}.png"  "${OUTPUT_DIR}/scenario.png" 2>/dev/null || true
  cp -f "${LATEST_BASE}.csv"  "${OUTPUT_DIR}/scenario.csv" 2>/dev/null || true
  cp -f "${LATEST_BASE}.json" "${OUTPUT_DIR}/scenario.json" 2>/dev/null || true
fi

# Generate a manifest for downstream consumers
cat > "${OUTPUT_DIR}/manifest.json" <<EOF
{
  "report_type": "gold_direct_v3",
  "target_end": "${TARGET_END}",
  "generated_at": "$(/bin/date '+%Y-%m-%dT%H:%M:%S%z')",
  "files": {
    "report_txt": "report.txt",
    "report_md": "report.md",
    "scenario_png": "scenario.png",
    "scenario_csv": "scenario.csv",
    "scenario_json": "scenario.json"
  }
}
EOF

echo ""
echo "Gold report written to ${OUTPUT_DIR}/report.txt (+ scenario bundle)"
