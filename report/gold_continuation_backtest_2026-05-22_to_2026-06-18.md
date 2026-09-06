# Gold Continuation Backtest (2026-05-22 to 2026-06-18)

- cutoff_date: 2026-05-22
- latest_trade_date: 2026-06-18
- latest_close: 937.96
- records: 190
- overall_direction_accuracy: 98.42%
- overall_confidence: 24.91
- note: variable-horizon evaluation includes partial latest targets, including T+1 into the latest trading day.

## Horizon Summary

| 周期   |   样本数 |   MAE(元/克) |   MAPE% |   方向准确率% |   平均信心度 |
|:-----|------:|-----------:|--------:|---------:|--------:|
| T+1  |    19 |       8.83 |    0.92 |    100   |    40.4 |
| T+2  |    19 |      15.27 |    1.62 |    100   |    33.4 |
| T+3  |    19 |      18    |    1.92 |    100   |    25.3 |
| T+4  |    19 |      22.04 |    2.35 |    100   |    26.9 |
| T+5  |    19 |      23.38 |    2.5  |    100   |    24.9 |
| T+6  |    19 |      23.06 |    2.47 |    100   |    20.8 |
| T+7  |    19 |      26.23 |    2.8  |     89.5 |    19.9 |
| T+8  |    19 |      30.44 |    3.24 |    100   |    19.5 |
| T+9  |    19 |      35.5  |    3.76 |     94.7 |    18.8 |
| T+10 |    19 |      37.6  |    3.98 |    100   |    19.2 |

## Bucket Summary

| 区间       |   样本数 |   MAPE% |   方向准确率% |   平均信心度 |
|:---------|------:|--------:|---------:|--------:|
| T+1~T+3  |    57 |    1.49 |    100   |    33   |
| T+4~T+5  |    38 |    2.43 |    100   |    25.9 |
| T+5~T+10 |   114 |    3.13 |     97.4 |    20.5 |

## By Target Date

| target_date   |   样本数 |    平均预测价 |    实际收盘 |   平均偏差率 |   方向准确率 |   平均信心度 |
|:--------------|------:|---------:|--------:|--------:|--------:|--------:|
| 2026-05-25    |    10 | 1012.97  | 1001.4  |   1.219 |     100 |   30.88 |
| 2026-05-26    |    10 | 1007.96  |  995    |   1.331 |     100 |   25.01 |
| 2026-05-27    |    10 | 1002.44  |  983.56 |   1.92  |     100 |   22.16 |
| 2026-05-28    |    10 |  997.704 |  961.18 |   3.8   |     100 |   22.34 |
| 2026-05-29    |    10 |  991.522 |  989.4  |   0.908 |      90 |   31.38 |
| 2026-06-01    |    10 |  990.429 |  983.58 |   1.079 |     100 |   29.18 |
| 2026-06-02    |    10 |  994.035 |  990.6  |   0.591 |      90 |   28.06 |
| 2026-06-03    |    10 |  989.683 |  977.08 |   1.29  |     100 |   25.1  |
| 2026-06-04    |    10 |  985.847 |  977.94 |   1.092 |     100 |   22.85 |
| 2026-06-05    |    10 |  984.653 |  974.02 |   1.288 |     100 |   18.35 |
| 2026-06-08    |    10 |  980.609 |  942.2  |   4.077 |     100 |   25.23 |
| 2026-06-09    |    10 |  975.2   |  947.04 |   2.973 |     100 |   24.93 |
| 2026-06-10    |    10 |  966.89  |  919.32 |   5.174 |     100 |   28.94 |
| 2026-06-11    |    10 |  961.3   |  895    |   7.408 |     100 |   27.17 |
| 2026-06-12    |    10 |  957.71  |  911.62 |   5.169 |     100 |   26.09 |
| 2026-06-15    |    10 |  950.589 |  938.94 |   2.83  |     100 |   27.76 |
| 2026-06-16    |    10 |  945.012 |  941.72 |   2.543 |     100 |   24.45 |
| 2026-06-17    |    10 |  942.283 |  942.94 |   2.089 |      90 |   15.13 |
| 2026-06-18    |    10 |  936.846 |  937.96 |   1.783 |     100 |   18.24 |

## Recent Volatile Targets

| origin_date   | target_date   |   horizon |   origin_close |   pred_close |   actual_close |   pred_delta |   actual_delta |   confidence |   ape_pct | dir_match   | direction_guard                      | confidence_guard                                                            | branch_name   |
|:--------------|:--------------|----------:|---------------:|-------------:|---------------:|-------------:|---------------:|-------------:|----------:|:------------|:-------------------------------------|:----------------------------------------------------------------------------|:--------------|
| 2026-06-16    | 2026-06-17    |         1 |         941.72 |       942.36 |         942.94 |         0.64 |           1.22 |         15   |  0.06151  | True        | short_trendup_classifier_release     | direction_guard_dampen|tiny_edge_confidence_dampen                          | trend_up      |
| 2026-06-15    | 2026-06-17    |         2 |         938.94 |       940.78 |         942.94 |         1.84 |           4    |         28   |  0.229071 | True        | none                                 | whipsaw_confidence_dampen|low_edge_confidence_dampen                        | trend_up      |
| 2026-06-12    | 2026-06-17    |         3 |         911.62 |       913.64 |         942.94 |         2.02 |          31.32 |          8.5 |  3.1073   | True        | near_bearish_decay                   | whipsaw_confidence_dampen|direction_guard_dampen|low_edge_confidence_dampen | trend_down    |
| 2026-06-11    | 2026-06-17    |         4 |         895    |       897.23 |         942.94 |         2.23 |          47.94 |         11.7 |  4.8476   | True        | mid_horizon_structure_decay          | direction_guard_dampen                                                      | trend_down    |
| 2026-06-10    | 2026-06-17    |         5 |         919.32 |       922.44 |         942.94 |         3.12 |          23.62 |         12.7 |  2.17405  | True        | washout_rebound_release              | direction_guard_dampen                                                      | trend_down    |
| 2026-06-09    | 2026-06-17    |         6 |         947.04 |       941.72 |         942.94 |        -5.32 |          -4.1  |         11.4 |  0.129383 | True        | none                                 | none                                                                        | normal        |
| 2026-06-08    | 2026-06-17    |         7 |         942.2  |       940.62 |         942.94 |        -1.58 |           0.74 |         14.1 |  0.246039 | False       | bearish_guard                        | direction_guard_dampen                                                      | trend_down    |
| 2026-06-05    | 2026-06-17    |         8 |         974.02 |       972.45 |         942.94 |        -1.57 |         -31.08 |          6.9 |  3.12957  | True        | bearish_guard                        | direction_guard_dampen                                                      |               |
| 2026-06-04    | 2026-06-17    |         9 |         977.94 |       976.27 |         942.94 |        -1.67 |         -35    |         20.5 |  3.53469  | True        | bearish_guard                        | direction_guard_dampen                                                      | trend_up      |
| 2026-06-03    | 2026-06-17    |        10 |         977.08 |       975.32 |         942.94 |        -1.76 |         -34.14 |         22.5 |  3.43394  | True        | bearish_guard                        | direction_guard_dampen                                                      | trend_down    |
| 2026-06-17    | 2026-06-18    |         1 |         942.94 |       941.98 |         937.96 |        -0.96 |          -4.98 |         27.9 |  0.42859  | True        | t1_rebound_exhaustion_guard          | direction_guard_dampen|low_edge_confidence_dampen                           | trend_up      |
| 2026-06-16    | 2026-06-18    |         2 |         941.72 |       936.09 |         937.96 |        -5.63 |          -3.76 |         35.2 |  0.199369 | True        | none                                 | none                                                                        | trend_up      |
| 2026-06-15    | 2026-06-18    |         3 |         938.94 |       937.83 |         937.96 |        -1.11 |          -0.98 |         14   |  0.01386  | True        | weak_trendup_fatigue_guard           | whipsaw_confidence_dampen|direction_guard_dampen|low_edge_confidence_dampen | trend_up      |
| 2026-06-12    | 2026-06-18    |         4 |         911.62 |       914.4  |         937.96 |         2.78 |          26.34 |         18.2 |  2.51183  | True        | mid_horizon_structure_decay          | whipsaw_confidence_dampen|direction_guard_dampen                            | trend_down    |
| 2026-06-11    | 2026-06-18    |         5 |         895    |       896.36 |         937.96 |         1.36 |          42.96 |         19.9 |  4.43516  | True        | delayed_capitulation_rebound_release | direction_guard_dampen                                                      | trend_down    |
| 2026-06-10    | 2026-06-18    |         6 |         919.32 |       922.12 |         937.96 |         2.8  |          18.64 |         11.5 |  1.68877  | True        | washout_rebound_release              | direction_guard_dampen                                                      | trend_down    |
| 2026-06-09    | 2026-06-18    |         7 |         947.04 |       931.75 |         937.96 |       -15.29 |          -9.08 |         13.2 |  0.662075 | True        | none                                 | none                                                                        | normal        |
| 2026-06-08    | 2026-06-18    |         8 |         942.2  |       940.51 |         937.96 |        -1.69 |          -4.24 |         15.5 |  0.271867 | True        | bearish_guard                        | direction_guard_dampen                                                      | trend_down    |
| 2026-06-05    | 2026-06-18    |         9 |         974.02 |       971.24 |         937.96 |        -2.78 |         -36.06 |          7.6 |  3.54813  | True        | bearish_guard                        | direction_guard_dampen                                                      |               |
| 2026-06-04    | 2026-06-18    |        10 |         977.94 |       976.18 |         937.96 |        -1.76 |         -39.98 |         19.4 |  4.0748   | True        | bearish_guard                        | direction_guard_dampen                                                      | trend_up      |
