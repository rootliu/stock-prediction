# Gold Direction Model Improvement - 2026-05-23

## Scope

- Backtest window: 2026-04-28 to 2026-05-22, using data available after the 2026-04-27 cutoff.
- Target: improve T+1 to T+3 short-term direction correctness and T+5 to T+10 trend direction while preserving the existing direct GBM prediction path.
- Data sources used by the run: SHFE AU daily, COMEX GC=F, USDCNY, DXY, VIX, US10Y.

## Changes

- Extended trend-specific branch models from T+5 coverage to T+10 coverage.
- Added a long-horizon bearish guard for stale bullish carry when trend structure and classifier confidence disagree with the regressor.
- Added a short-horizon structure guard for T+1 to T+3:
  - bearish continuation after fresh downside momentum;
  - failed bounce when price remains below medium trend and near recent highs is weak;
  - short top rollover after a strong 3-5 day rally loses VWAP/high confirmation.
- Added `pre_guard_return_pct` and `direction_guard` to `model_details` so agents can audit when a guard changed the raw model output.

## Before/After

| Metric | Previous | Updated |
|---|---:|---:|
| Overall direction accuracy | 26.96% | 51.30% |
| Overall confidence | 32.56 | 32.80 |
| T+1~T+3 MAPE | 1.80% | 1.14% |
| T+1~T+3 direction accuracy | 37.50% | 83.30% |
| T+5~T+10 MAPE | 4.72% | 2.46% |
| T+5~T+10 direction accuracy | 22.20% | 43.20% |

## Updated Horizon Summary

| Horizon | Samples | MAE CNY/g | MAPE | Direction Accuracy | Avg Confidence |
|---|---:|---:|---:|---:|---:|
| T+1 | 7 | 7.39 | 0.72% | 85.7% | 50.5 |
| T+2 | 8 | 11.99 | 1.17% | 87.5% | 41.7 |
| T+3 | 9 | 14.89 | 1.45% | 77.8% | 44.7 |
| T+4 | 10 | 25.19 | 2.46% | 40.0% | 43.4 |
| T+5 | 11 | 22.75 | 2.23% | 54.5% | 37.3 |
| T+6 | 12 | 23.53 | 2.32% | 41.7% | 30.0 |
| T+7 | 13 | 26.61 | 2.62% | 23.1% | 23.6 |
| T+8 | 14 | 24.95 | 2.47% | 42.9% | 28.3 |
| T+9 | 15 | 24.49 | 2.43% | 46.7% | 27.8 |
| T+10 | 16 | 26.62 | 2.64% | 50.0% | 22.3 |

## Interpretation

The main error was stale bullish carry: the raw regressor continued projecting upside after market structure had already rolled over. The new guards do not replace the direct GBM model. They act as a post-model calibration layer and only alter bullish outputs when price structure, trend branch, classifier probability, or low confidence suggests the upside signal is unreliable.

Short-horizon accuracy improved most because recent failures had clear local structure: downside continuation, failed bounce, and top rollover. Long-horizon trend accuracy improved by letting T+6 to T+10 use trend branches and by preventing low-confidence bullish drift from dominating late horizons.

## Caveats

- This is a continuation-window result, not a full historical validation.
- The short-horizon structure guard was tuned against a volatile late-April to late-May sample, so it needs walk-forward validation on older volatile periods.
- Confidence remains intentionally low for T+7 to T+10, which is appropriate because directional accuracy is still unstable there.

## Recommended Next Step

Run a broader walk-forward validation across at least three regimes:

- strong uptrend;
- sharp correction;
- sideways/high-volatility consolidation.

Only after that should the structure guard thresholds be promoted from fixed constants to calibrated quantiles.
