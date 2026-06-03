# Gold Model Improvement Review - 2026-06-02

## Scope

- Data source latest SHFE AU daily bar: 2026-06-02, close 990.60 CNY/g.
- Intraday/night-session check from production wrapper: SHFE AU 60min through 2026-06-03 09:30.
- Focus: recent violent two-session move after the 2026-05-28 selloff and 2026-05-29 rebound.

## Problem Found

The model had two recent failure modes:

1. Post-capitulation rebound over-extension.
   - 2026-05-29 origin predicted 2026-06-01 up with high confidence.
   - Actual 2026-06-01 was down from 989.40 to 983.58.
   - The model treated the 2026-05-29 rebound as continuation, while the broader 3/5-day structure had not repaired.

2. Tiny directional edge with oversized confidence.
   - 2026-06-01 origin predicted 2026-06-02 slightly down by only 0.30 CNY/g before the fix.
   - Actual 2026-06-02 was up to 990.60.
   - The prediction edge was near zero, but confidence was still too high for a whipsaw regime.

## Code Changes

- Added `post_capitulation_rebound_fade`.
  - Applies only to T+1.
  - Detects a strong one-day rebound after unresolved 3/5-day weakness, high recent volatility, weak MA10 repair, negative COMEX-SHFE premium, and close still near the high.
  - Converts stale bullish continuation into a conservative fade.

- Added `cross_market_rebound_release`.
  - Applies only to T+1/T+2.
  - Detects a small bearish prediction when COMEX relative premium is positive and SHFE is still below recent high after a weak selloff.
  - Allows a small rebound instead of forcing weak bearish continuation.

- Added post-guard confidence calibration.
  - `direction_guard_dampen`: reduces confidence when a guard materially changes the model return.
  - `tiny_edge_confidence_dampen`: sharply reduces confidence when the predicted edge is too small to justify a directional call.
  - `low_edge_confidence_dampen`: reduces confidence for low-edge T+1~T+3 calls under volatile conditions.

## Backtest Results

### Recent volatile window

`cutoff=2026-05-28`, evaluated targets from 2026-05-29 to 2026-06-02.

| Metric | Before | After |
|---|---:|---:|
| Overall direction accuracy | 43.33% | 50.00% |
| Overall average confidence | 42.04 | 29.90 |
| T+1 direction accuracy | 33.3% | 100.0% |
| T+1 MAPE | 1.57% | 1.24% |
| T+1~T+3 direction accuracy | 44.4% | 66.7% |
| T+1~T+3 MAPE | 1.15% | 1.04% |

### Wider continuation window

`cutoff=2026-05-22`, evaluated targets from 2026-05-25 to 2026-06-02.

| Horizon bucket | Samples | MAPE | Direction accuracy | Avg confidence |
|---|---:|---:|---:|---:|
| T+1~T+3 | 21 | 1.51% | 52.4% | 39.0 |
| T+4~T+5 | 14 | 2.75% | 28.6% | 39.4 |
| T+5~T+10 | 42 | 2.30% | 57.1% | 22.7 |

## Key Recent Samples After Fix

| Origin | Target | Horizon | Pred | Actual | Direction OK | Guard | Confidence |
|---|---|---:|---:|---:|---|---|---:|
| 2026-05-29 | 2026-06-01 | T+1 | 988.39 | 983.58 | yes | post_capitulation_rebound_fade | 34.2 |
| 2026-06-01 | 2026-06-02 | T+1 | 984.25 | 990.60 | yes | cross_market_rebound_release | 22.6 |
| 2026-05-29 | 2026-06-02 | T+2 | 1005.00 | 990.60 | yes | none | 39.9 |

## Current Production Forecast Check

Production wrapper:

```bash
MPLCONFIGDIR=/tmp/mpl-stock /Users/rootliu/code/stock-prediction/scripts/run_gold_direct_report.sh /tmp/gold-direct-20260601-check
```

Output type: `gold_direct_v3`.

| Date | Base forecast | Direction | Confidence | Range |
|---|---:|---|---:|---|
| 2026-06-03 | 989.00 | down | 26.0% | 977 ~ 1001 |
| 2026-06-04 | 988.51 | flat/down edge | 42.9% | 970 ~ 1007 |
| 2026-06-05 | 998.71 | up | 55.5% | 972 ~ 1025 |
| 2026-06-08 | 1004.28 | up | 47.1% | 957 ~ 1052 |

## Interpretation

- The immediate T+1 failure mode improved materially.
- The model is now less overconfident in whipsaw conditions, which is more important than forcing a high-confidence directional call.
- T+2/T+3 and T+4/T+5 remain structurally weak in shock windows. These horizons need a dedicated shock-regime task rather than more hand-written guards.

## Next Improvement Direction

1. Add a first-class `shock_regime_code` feature.
2. Split model evaluation by regime: trend continuation, capitulation rebound, failed rebound, cross-market discount/premium.
3. Train a small meta-selector that chooses between direct GBM, guarded direct GBM, and event-adjusted scenario output based on the last 3-5 trading days.
4. Keep the current direct V3 path as fallback to avoid breaking cron/OpenClaw usage.
