#!/bin/zsh
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="${1:-${GOLD_DIRECT_OUTPUT_DIR:-}}"
[[ -n "$OUTPUT_DIR" ]] || { echo "Usage: $0 <output-dir> [target-end]" >&2; exit 1; }
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/mpl-stock}"
exec "${ROOT_DIR}/.venv/bin/python" "${ROOT_DIR}/scripts/gold_publish.py" "$OUTPUT_DIR" "${2:-${GOLD_TARGET_END:-}}"
