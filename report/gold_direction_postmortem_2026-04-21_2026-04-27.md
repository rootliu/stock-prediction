# Gold Direction Postmortem (2026-04-21 to 2026-04-27)

## Scope

- Source backtest detail: `/Users/rootliu/code/stock-prediction/report/gold_direct_recent_backtest_detail_2026-04-27.csv`
- Source summary: `/Users/rootliu/code/stock-prediction/report/gold_direct_recent_backtest_review_2026-04-27.md`
- Focus window: `2026-04-21` to `2026-04-27`

## Headline

- The model's recent direction miss was real, but concentrated in `T+3 ~ T+5`.
- `T+1` was correct in this window, `T+2` was mixed, and `T+3+` collapsed.
- The core issue was not confidence inflation; confidence was already falling.
- The core issue was stale bullish trend carryover in mid/far horizons.

## By Target Date

| Target Date | Samples | Avg Pred | Actual | Avg APE | Direction Accuracy | Avg Confidence |
|---|---:|---:|---:|---:|---:|---:|
| 2026-04-21 | 5 | 1067.06 | 1051.70 | 1.568% | 20.0% | 44.46 |
| 2026-04-22 | 4 | 1066.76 | 1051.40 | 1.610% | 25.0% | 46.25 |
| 2026-04-23 | 3 | 1073.99 | 1040.06 | 3.262% | 0.0% | 35.43 |
| 2026-04-24 | 2 | 1074.84 | 1032.12 | 4.140% | 0.0% | 31.60 |
| 2026-04-27 | 1 | 1078.07 | 1039.42 | 3.718% | 0.0% | 23.50 |

## By Horizon

| Horizon | Samples | Avg APE | Direction Accuracy | Avg Confidence |
|---|---:|---:|---:|---:|
| T+1 | 1 | 0.268% | 100.0% | 81.10 |
| T+2 | 2 | 0.802% | 50.0% | 54.10 |
| T+3 | 3 | 2.204% | 0.0% | 48.07 |
| T+4 | 4 | 2.987% | 0.0% | 33.30 |
| T+5 | 5 | 3.126% | 0.0% | 26.72 |

## Branch Breakdown

| Branch | Horizon | Samples | Direction Accuracy | Avg Confidence | Avg APE |
|---|---:|---:|---:|---:|---:|
| jump_up | T+1 | 1 | 100.0% | 81.10 | 0.268% |
| jump_up | T+2 | 1 | 100.0% | 75.60 | 0.298% |
| normal | T+2 | 1 | 0.0% | 32.60 | 1.306% |
| normal | T+3 | 1 | 0.0% | 55.10 | 1.374% |
| normal | T+4 | 1 | 0.0% | 33.40 | 3.065% |
| normal | T+5 | 1 | 0.0% | 30.80 | 4.063% |
| trend_up | T+3 | 1 | 0.0% | 42.40 | 2.085% |
| trend_up | T+4 | 2 | 0.0% | 33.70 | 2.333% |
| trend_up | T+5 | 3 | 0.0% | 26.43 | 2.616% |
| base_only | T+3 | 1 | 0.0% | 46.70 | 3.154% |
| base_only | T+4 | 1 | 0.0% | 32.40 | 4.216% |
| base_only | T+5 | 1 | 0.0% | 23.50 | 3.718% |

## 2026-04-27 Case

There are two different ways to read the `2026-04-27` miss:

1. The stale `T+5` forecast issued from `2026-04-20`
   - origin: `2026-04-20`
   - target: `2026-04-27`
   - predicted: `1078.07`
   - actual: `1039.42`
   - APE: `3.718%`
   - confidence: `23.5`
   - result: wrong direction, wrong magnitude

2. A refreshed forecast built from the full `2026-04-24` close history
   - predicted: `1040.51`
   - actual: `1039.42`
   - APE: about `0.10%`
   - result: this was close

This means the system was not failing on same-day refreshed information. The main failure was stale medium-horizon carryover.

## Diagnosis

1. The model kept carrying bullish state too far into `T+3 ~ T+5`.
2. The trend branch helped on `T+3/T+4`, but not enough to fully flip direction.
3. `T+5` was the weakest regime even after trend extension.
4. Confidence was already low by `T+4/T+5`, but there was no neutral gating, so the system still emitted directional calls.

## Recommendations

1. Add a confidence gate for direction labels
   - for example: below `35`, emit `观望` instead of `涨/跌`
2. Increase negative trend veto power on `T+3 ~ T+5`
   - if `trend_down` is active and `ma_gap_5`, `ma_gap_10`, and slope are all negative, clamp positive returns harder
3. Add horizon-specific trend decay
   - reduce `trend_up` blend weight progressively from `T+3` onward during weakening regimes
4. Split direction and magnitude objectives
   - use a stricter direction head for `T+3 ~ T+5`, instead of trusting the regressor sign alone

## Practical Takeaway

- For this system's current state, `T+1` remains usable.
- `T+2` is conditional.
- `T+3 ~ T+5` should be treated as trend-scenario guidance, not hard directional calls.
