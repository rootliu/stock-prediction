# Gold Continuation Backtest (2026-05-28 to 2026-06-03)

- cutoff_date: 2026-05-28
- latest_trade_date: 2026-06-03
- latest_close: 977.08
- records: 40
- overall_direction_accuracy: 50.0%
- overall_confidence: 28.6
- note: variable-horizon evaluation includes partial latest targets, including T+1 into the latest trading day.

## Horizon Summary

| 周期   |   样本数 |   MAE(元/克) |   MAPE% |   方向准确率% |   平均信心度 |
|:-----|------:|-----------:|--------:|---------:|--------:|
| T+1  |     4 |      11.65 |    1.18 |      100 |    44   |
| T+2  |     4 |      12.22 |    1.24 |       50 |    43.8 |
| T+3  |     4 |       9.23 |    0.94 |       25 |    32   |
| T+4  |     4 |      12.18 |    1.24 |       50 |    33.9 |
| T+5  |     4 |      12.03 |    1.22 |       50 |    28.3 |
| T+6  |     4 |      15.2  |    1.54 |       25 |    20.8 |
| T+7  |     4 |      14.78 |    1.5  |        0 |    20.9 |
| T+8  |     4 |      10.71 |    1.09 |       50 |    20.6 |
| T+9  |     4 |      13.83 |    1.41 |       50 |    20.9 |
| T+10 |     4 |      10.9  |    1.11 |      100 |    20.9 |

## Bucket Summary

| 区间       |   样本数 |   MAPE% |   方向准确率% |   平均信心度 |
|:---------|------:|--------:|---------:|--------:|
| T+1~T+3  |    12 |    1.12 |     58.3 |    39.9 |
| T+4~T+5  |     8 |    1.23 |     50   |    31.1 |
| T+5~T+10 |    24 |    1.31 |     45.8 |    22.1 |

## By Target Date

| target_date   |   样本数 |   平均预测价 |   实际收盘 |   平均偏差率 |   方向准确率 |   平均信心度 |
|:--------------|------:|--------:|-------:|--------:|--------:|--------:|
| 2026-05-29    |    10 | 995.228 | 989.4  |   1.338 |      40 |   32.07 |
| 2026-06-01    |    10 | 992.878 | 983.58 |   1.357 |      50 |   27.79 |
| 2026-06-02    |    10 | 995.268 | 990.6  |   0.716 |      60 |   26.84 |
| 2026-06-03    |    10 | 992.489 | 977.08 |   1.577 |      50 |   27.7  |

## Recent Volatile Targets

| origin_date   | target_date   |   horizon |   origin_close |   pred_close |   actual_close |   pred_delta |   actual_delta |   confidence |   ape_pct | dir_match   | direction_guard              | confidence_guard                                   | branch_name   |
|:--------------|:--------------|----------:|---------------:|-------------:|---------------:|-------------:|---------------:|-------------:|----------:|:------------|:-----------------------------|:---------------------------------------------------|:--------------|
| 2026-06-01    | 2026-06-02    |         1 |         983.58 |       984.25 |         990.6  |         0.67 |           7.02 |         22.6 |  0.641026 | True        | cross_market_rebound_release | direction_guard_dampen|tiny_edge_confidence_dampen | trend_down    |
| 2026-05-29    | 2026-06-02    |         2 |         989.4  |      1005    |         990.6  |        15.6  |           1.2  |         39.9 |  1.45366  | True        | none                         | whipsaw_confidence_dampen                          | normal        |
| 2026-05-28    | 2026-06-02    |         3 |         961.18 |       992.99 |         990.6  |        31.81 |          29.42 |         51.5 |  0.241268 | True        | none                         | none                                               |               |
| 2026-05-27    | 2026-06-02    |         4 |         983.56 |       991.18 |         990.6  |         7.62 |           7.04 |         32   |  0.05855  | True        | mid_horizon_structure_decay  | direction_guard_dampen                             | trend_down    |
| 2026-05-26    | 2026-06-02    |         5 |         995    |       993.73 |         990.6  |        -1.27 |          -4.4  |         29.7 |  0.31597  | True        | bearish_guard                | direction_guard_dampen                             | trend_down    |
| 2026-05-25    | 2026-06-02    |         6 |        1001.4  |      1002.13 |         990.6  |         0.73 |         -10.8  |         10   |  1.16394  | False       | low_confidence_decay         | direction_guard_dampen|tiny_edge_confidence_dampen | trend_up      |
| 2026-05-22    | 2026-06-02    |         7 |         995.76 |       998.09 |         990.6  |         2.33 |          -5.16 |         20   |  0.756107 | False       | low_confidence_decay         | direction_guard_dampen                             | trend_up      |
| 2026-05-21    | 2026-06-02    |         8 |         995.38 |      1000.42 |         990.6  |         5.04 |          -4.78 |         21.4 |  0.991318 | False       | low_confidence_decay         | direction_guard_dampen                             | normal        |
| 2026-05-20    | 2026-06-02    |         9 |         986.64 |       984.84 |         990.6  |        -1.8  |           3.96 |         21.2 |  0.581466 | False       | bearish_guard                | direction_guard_dampen                             | trend_down    |
| 2026-05-19    | 2026-06-02    |        10 |        1002.18 |      1000.05 |         990.6  |        -2.13 |         -11.58 |         20.1 |  0.953967 | True        | bearish_guard                | direction_guard_dampen                             | normal        |
| 2026-06-02    | 2026-06-03    |         1 |         990.6  |       986.81 |         977.08 |        -3.79 |         -13.52 |         36.3 |  0.995824 | True        | none                         | none                                               | trend_up      |
| 2026-06-01    | 2026-06-03    |         2 |         983.58 |       985.76 |         977.08 |         2.18 |          -6.5  |         42.5 |  0.888361 | False       | near_bearish_decay           | direction_guard_dampen                             | trend_down    |
| 2026-05-29    | 2026-06-03    |         3 |         989.4  |       998.47 |         977.08 |         9.07 |         -12.32 |         17.1 |  2.18918  | False       | none                         | whipsaw_confidence_dampen                          | normal        |
| 2026-05-28    | 2026-06-03    |         4 |         961.18 |       990.97 |         977.08 |        29.79 |          15.9  |         47.1 |  1.42158  | True        | none                         | none                                               |               |
| 2026-05-27    | 2026-06-03    |         5 |         983.56 |       982.21 |         977.08 |        -1.35 |          -6.48 |         28.8 |  0.525034 | True        | bearish_guard                | direction_guard_dampen                             | trend_down    |
| 2026-05-26    | 2026-06-03    |         6 |         995    |       993.61 |         977.08 |        -1.39 |         -17.92 |         24.4 |  1.69178  | True        | bearish_guard                | direction_guard_dampen                             | trend_down    |
| 2026-05-25    | 2026-06-03    |         7 |        1001.4  |      1002.52 |         977.08 |         1.12 |         -24.32 |         20.5 |  2.60368  | False       | low_confidence_decay         | direction_guard_dampen                             | trend_up      |
| 2026-05-22    | 2026-06-03    |         8 |         995.76 |       997.85 |         977.08 |         2.09 |         -18.68 |         18.6 |  2.12572  | False       | low_confidence_decay         | direction_guard_dampen                             | trend_up      |
| 2026-05-21    | 2026-06-03    |         9 |         995.38 |      1001.94 |         977.08 |         6.56 |         -18.3  |         21   |  2.54432  | False       | low_confidence_decay         | direction_guard_dampen                             | normal        |
| 2026-05-20    | 2026-06-03    |        10 |         986.64 |       984.75 |         977.08 |        -1.89 |          -9.56 |         20.7 |  0.784992 | True        | bearish_guard                | direction_guard_dampen                             | trend_down    |
