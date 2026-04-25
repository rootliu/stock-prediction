# Gold Backtest Recommendations (2026-04-24)

## Findings

- T+1: MAPE 1.25%, direction 66.7%, jump ratio 0.0%, branch usage 100.0%
- T+2: MAPE 1.35%, direction 61.1%, jump ratio 0.0%, branch usage 100.0%
- T+3: MAPE 1.48%, direction 55.6%, jump ratio 0.0%, branch usage 100.0%
- T+4: MAPE 1.55%, direction 61.1%, jump ratio 0.0%, branch usage 100.0%
- T+5: MAPE 2.12%, direction 50.0%, jump ratio 0.0%, branch usage 100.0%

## Suggestions

- Keep the quantile-based jump labeling; it is now activating branch paths on real recent data.
- If T+2 remains sticky, add horizon-specific COMEX acceleration and overnight premium slope features.
- If branch usage rises but accuracy stalls, calibrate blend weights by branch instead of using fixed weights.
- Continue treating the event layer as explanatory rather than primary alpha.