# Gold Daily 16:00 Forecast

- generated_at: 2026-03-26T07:15:35
- forecast_basis: 4h model timeline with the daily 16:00 point treated as the day result
- live_snapshot_sources: SGE_AU9999, SHFE_AU_MAIN, COMEX, US_ETF

## Market Snapshot

- SGE Au99.99 Spot (SGE_AU9999 / spot): latest_price=1015.45, latest_timestamp=2026-03-25, session=ALL
- SHFE Gold Main (SHFE_AU_MAIN / futures): latest_price=1016.92, latest_timestamp=2026-03-26 02:30, session=NIGHT
- COMEX Gold Futures (COMEX / futures): latest_price=4498.7001953125, latest_timestamp=2026-03-25, session=ALL
- GLD Spot Proxy (US_ETF / spot_proxy): latest_price=416.2900085449219, latest_timestamp=2026-03-25, session=ALL

| source | label | category | latest_price | latest_timestamp | market_group | session |
| --- | --- | --- | --- | --- | --- | --- |
| SGE_AU9999 | SGE Au99.99 Spot | spot | 1015.45 | 2026-03-25 | DOMESTIC | ALL |
| SHFE_AU_MAIN | SHFE Gold Main | futures | 1016.92 | 2026-03-26 02:30 | DOMESTIC | NIGHT |
| COMEX | COMEX Gold Futures | futures | 4498.7001953125 | 2026-03-25 | FOREIGN | ALL |
| US_ETF | GLD Spot Proxy | spot_proxy | 416.2900085449219 | 2026-03-25 | FOREIGN | ALL |

## Forecast Table

| label | category | model_type | forecast_date | forecast_close | direction | confidence_pct | mape | direction_accuracy | history_rows | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SHFE Gold Main | futures | linear | 2026-03-26 16:00 | 1138.25 | bullish | 99.48 | 2.1422 | 50.0 | 115 | ok |
| SHFE Gold Main | futures | linear | 2026-03-27 16:00 | 1219.23 | bullish | 36.27 | 2.1422 | 50.0 | 115 | ok |
| SHFE Gold Main | futures | linear | 2026-03-28 16:00 | 1054.29 | bullish | 98.94 | 2.1422 | 50.0 | 115 | ok |
| SHFE Gold Main | futures | linear | 2026-03-29 16:00 | 1020.15 | bullish | 65.97 | 2.1422 | 50.0 | 115 | ok |
| SHFE Gold Main | futures | linear | 2026-03-30 16:00 | 1182.92 | bullish | 85.2 | 2.1422 | 50.0 | 115 | ok |
| SHFE Gold Main | futures | boosting | 2026-03-26 16:00 | 1016.12 | bearish | 90.88 | 1.6301 | 50.0 | 115 | ok |
| SHFE Gold Main | futures | boosting | 2026-03-27 16:00 | 1048.05 | bullish | 85.6 | 1.6301 | 50.0 | 115 | ok |
| SHFE Gold Main | futures | boosting | 2026-03-28 16:00 | 1081.51 | bullish | 31.66 | 1.6301 | 50.0 | 115 | ok |
| SHFE Gold Main | futures | boosting | 2026-03-29 16:00 | 1102.56 | bullish | 89.96 | 1.6301 | 50.0 | 115 | ok |
| SHFE Gold Main | futures | boosting | 2026-03-30 16:00 | 1103.65 | bullish | 16.48 | 1.6301 | 50.0 | 115 | ok |
| SHFE Gold Main | futures | ensemble | 2026-03-26 16:00 | 1034.33 | bullish | 56.64 | 2.0042 | 47.86 | 115 | ok |
| SHFE Gold Main | futures | ensemble | 2026-03-27 16:00 | 1124.41 | bullish | 91.15 | 2.0042 | 47.86 | 115 | ok |
| SHFE Gold Main | futures | ensemble | 2026-03-28 16:00 | 1182.14 | bullish | 57.99 | 2.0042 | 47.86 | 115 | ok |
| SHFE Gold Main | futures | ensemble | 2026-03-29 16:00 | 1235.1 | bullish | 93.83 | 2.0042 | 47.86 | 115 | ok |
| SHFE Gold Main | futures | ensemble | 2026-03-30 16:00 | 1278.9 | bullish | 48.66 | 2.0042 | 47.86 | 115 | ok |
| COMEX Gold Futures | futures | linear | 2026-03-26 16:00 | 4455.22 | bearish | 37.49 | 2.5099 | 45.0 | 1518 | ok |
| COMEX Gold Futures | futures | linear | 2026-03-27 16:00 | 3872.61 | bearish | 79.68 | 2.5099 | 45.0 | 1518 | ok |
| COMEX Gold Futures | futures | linear | 2026-03-28 16:00 | 3554.9 | bearish | 91.75 | 2.5099 | 45.0 | 1518 | ok |
| COMEX Gold Futures | futures | linear | 2026-03-29 16:00 | 3296.48 | bearish | 90.33 | 2.5099 | 45.0 | 1518 | ok |
| COMEX Gold Futures | futures | linear | 2026-03-30 16:00 | 3056.84 | bearish | 88.73 | 2.5099 | 45.0 | 1518 | ok |
| COMEX Gold Futures | futures | boosting | 2026-03-26 16:00 | 4484.74 | bearish | 37.83 | 1.4662 | 60.0 | 1518 | ok |
| COMEX Gold Futures | futures | boosting | 2026-03-27 16:00 | 4405.86 | bearish | 56.22 | 1.4662 | 60.0 | 1518 | ok |
| COMEX Gold Futures | futures | boosting | 2026-03-28 16:00 | 4279.64 | bearish | 68.21 | 1.4662 | 60.0 | 1518 | ok |
| COMEX Gold Futures | futures | boosting | 2026-03-29 16:00 | 4114.78 | bearish | 79.75 | 1.4662 | 60.0 | 1518 | ok |
| COMEX Gold Futures | futures | boosting | 2026-03-30 16:00 | 3908.46 | bearish | 77.77 | 1.4662 | 60.0 | 1518 | ok |
| COMEX Gold Futures | futures | ensemble | 2026-03-26 16:00 | 4475.11 | bearish | 9.46 | 1.9264 | 54.85 | 1518 | ok |
| COMEX Gold Futures | futures | ensemble | 2026-03-27 16:00 | 4204.84 | bearish | 2.63 | 1.9264 | 54.85 | 1518 | ok |
| COMEX Gold Futures | futures | ensemble | 2026-03-28 16:00 | 4005.68 | bearish | 10.5 | 1.9264 | 54.85 | 1518 | ok |
| COMEX Gold Futures | futures | ensemble | 2026-03-29 16:00 | 3810.57 | bearish | 18.08 | 1.9264 | 54.85 | 1518 | ok |
| COMEX Gold Futures | futures | ensemble | 2026-03-30 16:00 | 3594.52 | bearish | 16.78 | 1.9264 | 54.85 | 1518 | ok |
| GLD Spot Proxy | spot_proxy | linear | 2026-03-26 16:00 | 424.12 | bullish | 82.91 | 1.6665 | 40.0 | 581 | ok |
| GLD Spot Proxy | spot_proxy | linear | 2026-03-27 16:00 | 481.64 | bullish | 91.72 | 1.6665 | 40.0 | 581 | ok |
| GLD Spot Proxy | spot_proxy | linear | 2026-03-28 16:00 | 530.24 | bullish | 89.01 | 1.6665 | 40.0 | 581 | ok |
| GLD Spot Proxy | spot_proxy | linear | 2026-03-29 16:00 | 536.95 | bullish | 20.7 | 1.6665 | 40.0 | 581 | ok |
| GLD Spot Proxy | spot_proxy | linear | 2026-03-30 16:00 | 484.2 | bullish | 84.76 | 1.6665 | 40.0 | 581 | ok |
| GLD Spot Proxy | spot_proxy | boosting | 2026-03-26 16:00 | 424.08 | bullish | 20.77 | 2.5046 | 25.0 | 581 | ok |
| GLD Spot Proxy | spot_proxy | boosting | 2026-03-27 16:00 | 424.85 | bullish | 87.37 | 2.5046 | 25.0 | 581 | ok |
| GLD Spot Proxy | spot_proxy | boosting | 2026-03-28 16:00 | 413.25 | bearish | 76.12 | 2.5046 | 25.0 | 581 | ok |
| GLD Spot Proxy | spot_proxy | boosting | 2026-03-29 16:00 | 396.79 | bearish | 83.89 | 2.5046 | 25.0 | 581 | ok |
| GLD Spot Proxy | spot_proxy | boosting | 2026-03-30 16:00 | 398.57 | bearish | 18.61 | 2.5046 | 25.0 | 581 | ok |
| GLD Spot Proxy | spot_proxy | ensemble | 2026-03-26 16:00 | 408.49 | bearish | 57.73 | 2.1112 | 30.79 | 581 | ok |
| GLD Spot Proxy | spot_proxy | ensemble | 2026-03-27 16:00 | 407.72 | bearish | 34.42 | 2.1112 | 30.79 | 581 | ok |
| GLD Spot Proxy | spot_proxy | ensemble | 2026-03-28 16:00 | 380.05 | bearish | 25.78 | 2.1112 | 30.79 | 581 | ok |
| GLD Spot Proxy | spot_proxy | ensemble | 2026-03-29 16:00 | 360.6 | bearish | 22.5 | 2.1112 | 30.79 | 581 | ok |
| GLD Spot Proxy | spot_proxy | ensemble | 2026-03-30 16:00 | 349.59 | bearish | 50.01 | 2.1112 | 30.79 | 581 | ok |

## Summary

- SHFE Gold Main: best current balance is boosting (MAPE=1.6301, direction_accuracy=50.0%, first_daily_1600=2026-03-26 16:00, confidence=90.88%).
- COMEX Gold Futures: best current balance is boosting (MAPE=1.4662, direction_accuracy=60.0%, first_daily_1600=2026-03-26 16:00, confidence=37.83%).
- GLD Spot Proxy: best current balance is linear (MAPE=1.6665, direction_accuracy=40.0%, first_daily_1600=2026-03-26 16:00, confidence=82.91%).

## Limitations

- SGE Au99.99 is included as a live spot anchor, but its provider does not expose enough historical intraday bars for a stable 4h forecast run.
- XAUUSD spot proxy from Yahoo (`XAUUSD=X`) is currently unavailable, so the foreign spot view uses `GLD` as the spot proxy.
- SHFE 4h history is materially shorter than COMEX 4h history, so SHFE model metrics should be treated as lower-confidence calibration.

## Improvement Ideas

- Add a dedicated SGE intraday history source or local archive so spot data can join the full 4h model pipeline instead of snapshot-only mode.
- Add a cross-market feature block using SGE spot, SHFE futures, COMEX futures, and GLD spreads as joint inputs instead of separate context rows.
- Add a formal rolling 4h backtest for sources with enough history and downgrade to holdout metrics only when bar counts are insufficient.