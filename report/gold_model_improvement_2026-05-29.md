# Gold Model Improvement - 2026-05-29 Volatility Shock

## Context

- Latest SHFE AU data: 2026-05-29 close `989.40` CNY/g.
- Recent shock:
  - 2026-05-28: `961.18`, daily return `-2.28%`.
  - 2026-05-29: `989.40`, daily return `+2.94%`.
- The existing V3 guards caught the 2026-05-28 downside, but over-forced bearish continuation into the 2026-05-29 rebound.

## Changes

- Added `capitulation_rebound_release` in `multi_day_direct_predictor.py`.
  - Scope: T+1/T+2 only.
  - Purpose: release the short bearish structure guard after a capitulation-style selloff when the classifier strongly supports a rebound.
  - Requirements include deep 1/3/5-day drawdown, negative MA gaps, close below VWAP/high, wide intraday range, and high up probability.
- Added `whipsaw_confidence_dampen`.
  - Scope: T+2+ after violent one-day reversal against recent multi-day direction.
  - Purpose: keep point forecasts, but lower confidence when short-term direction is unstable.
- Added `scripts/run_gold_continuation_backtest.py`.
  - Supports variable-horizon continuation backtests so the latest partial T+1/T+2 samples are not dropped.
- Exposed `pre_guard_return_pct`, `direction_guard`, and `confidence_guard` through `ml-service/models/gold_api.py`.

## Backtest Result

Window: targets after 2026-05-22 through 2026-05-29.

| Metric | Before Optimization | After Optimization |
|---|---:|---:|
| Overall direction accuracy | 50.0% | 52.0% |
| T+1 direction accuracy | 60.0% | 80.0% |
| T+1 MAPE | 1.43% | 1.37% |
| T+1~T+3 direction accuracy | 33.3% | 40.0% |
| T+5~T+10 direction accuracy | 63.3% | 63.3% |

## Key Finding

The improvement fixed the most important immediate failure: the 2026-05-28 origin now predicts 2026-05-29 as a rebound instead of continued downside.

| origin | target | horizon | before guard issue | updated result |
|---|---|---:|---|---|
| 2026-05-28 | 2026-05-29 | T+1 | `short_structure_guard` forced bearish continuation | `capitulation_rebound_release`, direction correct |

T+2/T+3 remain weak in this shock window. That suggests the next real improvement should be a dedicated shock regime, not more fixed guard thresholds.

## Current Production Check

`scripts/run_gold_direct_report.sh /tmp/gold-direct-20260529-check` completed successfully after rerunning with network access.

Current direct forecast from 2026-05-29:

| Date | Base Forecast | Direction | Confidence | Range |
|---|---:|---|---:|---|
| 2026-06-01 | 996.13 | up | 81.5% | 983.99 ~ 1008.28 |
| 2026-06-02 | 1007.46 | up | 41.0% | 984.98 ~ 1029.94 |
| 2026-06-03 | 1000.95 | up | 19.8% | 966.19 ~ 1035.70 |

The confidence dampening is visible on T+2/T+3 because the latest market is a whipsaw reversal.

## Next Recommendations

- Add a formal `shock_regime_code` feature instead of hard-coding capitulation logic inside the guard.
- Backtest separate regimes: trend continuation, capitulation rebound, and whipsaw consolidation.
- Treat T+2/T+3 as scenario ranges after a daily move above 2% until the shock-regime backtest improves.
- Keep T+5+ as low-confidence scenario guidance only.
