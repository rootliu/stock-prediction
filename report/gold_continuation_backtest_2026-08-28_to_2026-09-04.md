# Gold Continuation Backtest (2026-08-28 to 2026-09-04)

- cutoff_date: 2026-08-28
- latest_trade_date: 2026-09-04
- latest_close: 965.96
- records: 50
- overall_direction_accuracy: 66.0%
- overall_confidence: 27.15
- note: variable-horizon evaluation includes partial latest targets, including T+1 into the latest trading day.

## Horizon Summary

| 周期   |   样本数 |   MAE(元/克) |   MAPE% |   方向准确率% |   平均信心度 |
|:-----|------:|-----------:|--------:|---------:|--------:|
| T+1  |     5 |      11.98 |    1.25 |       60 |    48.7 |
| T+2  |     5 |      24.21 |    2.53 |       60 |    34.4 |
| T+3  |     5 |      27.42 |    2.87 |       60 |    24   |
| T+4  |     5 |      29.38 |    3.09 |       80 |    23.7 |
| T+5  |     5 |      31.94 |    3.35 |       80 |    31.8 |
| T+6  |     5 |      29.41 |    3.08 |      100 |    27.3 |
| T+7  |     5 |      16.3  |    1.71 |       80 |    28.2 |
| T+8  |     5 |      19.42 |    2.04 |       60 |    20   |
| T+9  |     5 |      24.3  |    2.55 |       40 |    16   |
| T+10 |     5 |      11.95 |    1.24 |       40 |    17.4 |

## Bucket Summary

| 区间       |   样本数 |   MAPE% |   方向准确率% |   平均信心度 |
|:---------|------:|--------:|---------:|--------:|
| T+1~T+3  |    15 |    2.22 |     60   |    35.7 |
| T+4~T+5  |    10 |    3.22 |     80   |    27.7 |
| T+5~T+10 |    30 |    2.33 |     66.7 |    23.4 |

## By Target Date

| target_date   |   样本数 |   平均预测价 |   实际收盘 |   平均偏差率 |   方向准确率 |   平均信心度 |
|:--------------|------:|--------:|-------:|--------:|--------:|--------:|
| 2026-08-31    |    10 | 976.365 | 961.92 |   2.127 |      60 |   22.99 |
| 2026-09-01    |    10 | 978.319 | 959.94 |   2.295 |      60 |   22.11 |
| 2026-09-02    |    10 | 972.63  | 938.22 |   3.668 |      90 |   30.5  |
| 2026-09-03    |    10 | 969.867 | 958.38 |   1.984 |      70 |   32.37 |
| 2026-09-04    |    10 | 971.465 | 965.96 |   1.786 |      50 |   27.79 |

## Recent Volatile Targets

| origin_date   | target_date   |   horizon |   origin_close |   pred_close |   actual_close |   pred_delta |   actual_delta |   confidence |   ape_pct | dir_match   | direction_guard                | confidence_guard                                  | branch_name   |
|:--------------|:--------------|----------:|---------------:|-------------:|---------------:|-------------:|---------------:|-------------:|----------:|:------------|:-------------------------------|:--------------------------------------------------|:--------------|
| 2026-09-02    | 2026-09-03    |         1 |         938.22 |       937.42 |         958.38 |        -0.8  |          20.16 |         36   |  2.18702  | False       | short_structure_guard          | direction_guard_dampen|low_edge_confidence_dampen | trend_down    |
| 2026-09-01    | 2026-09-03    |         2 |         959.94 |       942.85 |         958.38 |       -17.09 |          -1.56 |         60.3 |  1.62044  | True        | none                           | none                                              | trend_down    |
| 2026-08-31    | 2026-09-03    |         3 |         961.92 |       960.5  |         958.38 |        -1.42 |          -3.54 |         17.4 |  0.221207 | True        | near_breakdown_guard           | direction_guard_dampen|low_edge_confidence_dampen | trend_down    |
| 2026-08-28    | 2026-09-03    |         4 |         999.28 |       979.11 |         958.38 |       -20.17 |         -40.9  |         45.8 |  2.16303  | True        | none                           | none                                              | trend_up      |
| 2026-08-27    | 2026-09-03    |         5 |         995.3  |       990.1  |         958.38 |        -5.2  |         -36.92 |         38.8 |  3.30975  | True        | none                           | none                                              | trend_down    |
| 2026-08-26    | 2026-09-03    |         6 |        1003    |       988.84 |         958.38 |       -14.16 |         -44.62 |         36   |  3.17828  | True        | none                           | none                                              | trend_down    |
| 2026-08-25    | 2026-09-03    |         7 |        1004.22 |       957.24 |         958.38 |       -46.98 |         -45.84 |         31.9 |  0.118951 | True        | none                           | none                                              | trend_up      |
| 2026-08-24    | 2026-09-03    |         8 |        1006.82 |       976.17 |         958.38 |       -30.65 |         -48.44 |         28.7 |  1.85626  | True        | none                           | none                                              | trend_up      |
| 2026-08-21    | 2026-09-03    |         9 |         987.44 |       988.85 |         958.38 |         1.41 |         -29.06 |          8.4 |  3.17932  | False       | low_confidence_decay           | direction_guard_dampen                            | trend_up      |
| 2026-08-20    | 2026-09-03    |        10 |         972.94 |       977.59 |         958.38 |         4.65 |         -14.56 |         20.4 |  2.00442  | False       | low_confidence_decay           | direction_guard_dampen                            | trend_up      |
| 2026-09-03    | 2026-09-04    |         1 |         958.38 |       957.4  |         965.96 |        -0.98 |           7.58 |         33.7 |  0.886165 | False       | post_capitulation_rebound_fade | direction_guard_dampen|low_edge_confidence_dampen | normal        |
| 2026-09-02    | 2026-09-04    |         2 |         938.22 |       937.09 |         965.96 |        -1.13 |          27.74 |         21.4 |  2.98874  | False       | short_structure_guard          | direction_guard_dampen|low_edge_confidence_dampen | trend_down    |
| 2026-09-01    | 2026-09-04    |         3 |         959.94 |       950.54 |         965.96 |        -9.4  |           6.02 |         37.3 |  1.59634  | False       | none                           | none                                              | trend_down    |
| 2026-08-31    | 2026-09-04    |         4 |         961.92 |       960.09 |         965.96 |        -1.83 |           4.04 |         19.2 |  0.607686 | False       | mid_horizon_breakdown_guard    | direction_guard_dampen                            | trend_down    |
| 2026-08-28    | 2026-09-04    |         5 |         999.28 |       969.74 |         965.96 |       -29.54 |         -33.32 |         42.5 |  0.391321 | True        | none                           | none                                              | trend_up      |
| 2026-08-27    | 2026-09-04    |         6 |         995.3  |       989.02 |         965.96 |        -6.28 |         -29.34 |         29.6 |  2.38726  | True        | none                           | none                                              | trend_down    |
| 2026-08-26    | 2026-09-04    |         7 |        1003    |       987.04 |         965.96 |       -15.96 |         -37.04 |         33.1 |  2.18228  | True        | none                           | none                                              | trend_down    |
| 2026-08-25    | 2026-09-04    |         8 |        1004.22 |       974.34 |         965.96 |       -29.88 |         -38.26 |         22.2 |  0.867531 | True        | none                           | none                                              | trend_up      |
| 2026-08-24    | 2026-09-04    |         9 |        1006.82 |       998.38 |         965.96 |        -8.44 |         -40.86 |         18.5 |  3.35625  | True        | none                           | none                                              | trend_up      |
| 2026-08-21    | 2026-09-04    |        10 |         987.44 |       991.01 |         965.96 |         3.57 |         -21.48 |         20.4 |  2.59328  | False       | low_confidence_decay           | direction_guard_dampen                            | trend_up      |
