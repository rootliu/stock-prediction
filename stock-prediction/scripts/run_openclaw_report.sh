#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="${1:-${OPENCLAW_OUTPUT_DIR:-}}"
REPORT_SOURCE="${OPENCLAW_REPORT_SOURCE:-SHFE_AU_MAIN}"
HORIZON="${OPENCLAW_HORIZON:-5}"
LOOKBACK="${OPENCLAW_LOOKBACK:-240}"
COMPARE_DAYS="${OPENCLAW_COMPARE_DAYS:-180}"
SESSION_DAYS="${OPENCLAW_SESSION_DAYS:-5}"
SESSION_PERIOD="${OPENCLAW_SESSION_PERIOD:-15min}"

if [[ -z "${OUTPUT_DIR}" ]]; then
  echo "Usage: $0 <openclaw-output-dir>"
  echo "Or set OPENCLAW_OUTPUT_DIR in the environment."
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"

exec python3 "${ROOT_DIR}/run.py" \
  --bot-output-dir "${OUTPUT_DIR}" \
  --report-source "${REPORT_SOURCE}" \
  --horizon "${HORIZON}" \
  --lookback "${LOOKBACK}" \
  --compare-days "${COMPARE_DAYS}" \
  --session-days "${SESSION_DAYS}" \
  --session-period "${SESSION_PERIOD}"
