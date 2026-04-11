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

if [[ -z "${TARGET_END}" ]]; then
  TARGET_END="$("${PYTHON_BIN}" - <<'PY'
import akshare as ak
import pandas as pd
from datetime import date, timedelta

today = pd.Timestamp(date.today()).normalize()
try:
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
    d = today.date()
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

MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/mpl-stock}" \
PYTHONUNBUFFERED=1 \
"${PYTHON_BIN}" "${ROOT_DIR}/run_gold_analysis.py" \
  --forecast-mode direct \
  --skip-backtest \
  --target-end "${TARGET_END}" \
  --report-dir "${OUTPUT_DIR}"

LATEST_MD="$(/bin/ls -1t "${OUTPUT_DIR}"/gold_direct_scenario_*.md 2>/dev/null | head -n 1)"

if [[ -z "${LATEST_MD}" ]]; then
  echo "No gold_direct_scenario_*.md generated in ${OUTPUT_DIR}" >&2
  exit 1
fi

LATEST_BASE="${LATEST_MD%.md}"
LATEST_NAME="$(basename "${LATEST_BASE}")"
LATEST_DATE="${LATEST_NAME#gold_direct_scenario_}"

cp "${LATEST_BASE}.md" "${OUTPUT_DIR}/report.md"
cp "${LATEST_BASE}.png" "${OUTPUT_DIR}/scenario.png"
cp "${LATEST_BASE}.csv" "${OUTPUT_DIR}/scenario.csv"
cp "${LATEST_BASE}.json" "${OUTPUT_DIR}/scenario.json"

cat > "${OUTPUT_DIR}/manifest.json" <<EOF
{
  "report_type": "gold_direct_scenario",
  "latest_date": "${LATEST_DATE}",
  "target_end": "${TARGET_END}",
  "generated_at": "$(/bin/date '+%Y-%m-%dT%H:%M:%S%z')",
  "files": {
    "report_md": "report.md",
    "scenario_png": "scenario.png",
    "scenario_csv": "scenario.csv",
    "scenario_json": "scenario.json"
  }
}
EOF

echo "Gold direct report bundle written to ${OUTPUT_DIR}"
