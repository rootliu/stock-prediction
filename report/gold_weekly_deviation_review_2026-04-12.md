# Gold Weekly Deviation Review 2026-04-12

## Latest Snapshot

| Item | Value |
|---|---:|
| SHFE AU latest daily close | 1048.36 |
| Latest daily date | 2026-04-10 |
| COMEX converted close | 1045.42 |
| SHFE-COMEX spread | +2.94 |
| Regime | HIGH |
| Annualized volatility | 49.0% |

## Latest Backtest

| Horizon | MAPE | Direction Accuracy | Avg Confidence |
|---|---:|---:|---:|
| T+1 | 0.84% | 55.7% | 44.1% |
| T+2 | 1.35% | 45.7% | 41.0% |
| T+3 | 1.56% | 47.1% | 37.2% |
| T+4 | 1.72% | 54.3% | 35.8% |
| T+5 | 2.17% | 48.6% | 30.1% |

## Event Interval Backtest

| Horizon | Base Hit Rate | Event Hit Rate | Improvement | Base Width | Event Width |
|---|---:|---:|---:|---:|---:|
| T+1 | 57.1% | 57.1% | 0.0% | 1.66% | 1.67% |
| T+2 | 60.0% | 60.0% | 0.0% | 2.81% | 2.81% |
| T+3 | 74.3% | 74.3% | 0.0% | 3.96% | 3.96% |
| T+4 | 75.7% | 75.7% | 0.0% | 5.17% | 5.17% |
| T+5 | 74.3% | 74.3% | 0.0% | 6.42% | 6.27% |

## Last Week Forecast Deviations

| Issue Date | Target Date | Predicted | Actual Close | Abs Error | Pct Error | In Base Range |
|---|---|---:|---:|---:|---:|---|
| 2026-03-30 | 2026-04-01 | 1028.68 | 1053.18 | -24.50 | -2.33% | Yes |
| 2026-03-31 | 2026-04-01 | 1034.52 | 1053.18 | -18.66 | -1.77% | Yes |
| 2026-03-30 | 2026-04-02 | 1025.31 | 1023.78 | +1.53 | +0.15% | Yes |
| 2026-03-31 | 2026-04-02 | 1033.66 | 1023.78 | +9.88 | +0.97% | Yes |
| 2026-03-30 | 2026-04-03 | 1034.86 | 1033.00 | +1.86 | +0.18% | Yes |
| 2026-03-31 | 2026-04-03 | 1034.15 | 1033.00 | +1.15 | +0.11% | Yes |
| 2026-04-03 | 2026-04-07 | 1041.08 | 1034.28 | +6.80 | +0.66% | Yes |
| 2026-04-03 | 2026-04-08 | 1043.73 | 1062.00 | -18.27 | -1.72% | Yes |
| 2026-04-03 | 2026-04-09 | 1037.53 | 1041.32 | -3.79 | -0.36% | Yes |
| 2026-04-08 | 2026-04-09 | 1052.64 | 1041.32 | +11.32 | +1.09% | Yes |
| 2026-04-03 | 2026-04-10 | 1033.54 | 1048.36 | -14.82 | -1.41% | Yes |
| 2026-04-08 | 2026-04-10 | 1053.93 | 1048.36 | +5.57 | +0.53% | Yes |

## Readout

1. The largest misses still happen on jump days.
   - 2026-04-01 and 2026-04-08 remain the two biggest upside underestimation days.
2. Nearer forecasts converge better.
   - For 2026-04-10, the earlier 2026-04-03 issue missed by -14.82, while the nearer 2026-04-08 issue missed by only +5.57.
3. Base ranges are still doing their job.
   - Every reviewed target day stayed inside the base interval.
4. The model is stable, but single-point levels remain vulnerable to sudden acceleration.
