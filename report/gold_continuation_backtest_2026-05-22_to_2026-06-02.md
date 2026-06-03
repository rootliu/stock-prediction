# Gold Continuation Backtest (2026-05-22 to 2026-06-02)

- cutoff_date: 2026-05-22
- latest_trade_date: 2026-06-02
- latest_close: 990.60
- records: 70
- overall_direction_accuracy: 52.86%
- overall_confidence: 29.88
- note: variable-horizon evaluation includes partial latest targets, including T+1 into the latest trading day.

## Horizon Summary

| 周期   |   样本数 |   MAE(元/克) |   MAPE% |   方向准确率% |   平均信心度 |
|:-----|------:|-----------:|--------:|---------:|--------:|
| T+1  |     7 |      11.15 |    1.14 |     85.7 |    38.6 |
| T+2  |     7 |      17.68 |    1.8  |     42.9 |    42.1 |
| T+3  |     7 |      15.67 |    1.6  |     28.6 |    36.2 |
| T+4  |     7 |      30.88 |    3.14 |     28.6 |    45.8 |
| T+5  |     7 |      23.08 |    2.35 |     28.6 |    33   |
| T+6  |     7 |      12.76 |    1.3  |     57.1 |    21.2 |
| T+7  |     7 |      17.27 |    1.76 |     57.1 |    21.3 |
| T+8  |     7 |      21.56 |    2.19 |     71.4 |    21.1 |
| T+9  |     7 |      28.06 |    2.85 |     57.1 |    20   |
| T+10 |     7 |      32.59 |    3.32 |     71.4 |    19.5 |

## Bucket Summary

| 区间       |   样本数 |   MAPE% |   方向准确率% |   平均信心度 |
|:---------|------:|--------:|---------:|--------:|
| T+1~T+3  |    21 |    1.51 |     52.4 |    39   |
| T+4~T+5  |    14 |    2.75 |     28.6 |    39.4 |
| T+5~T+10 |    42 |    2.3  |     57.1 |    22.7 |

## By Target Date

| target_date   |   样本数 |    平均预测价 |    实际收盘 |   平均偏差率 |   方向准确率 |   平均信心度 |
|:--------------|------:|---------:|--------:|--------:|--------:|--------:|
| 2026-05-25    |    10 | 1018.3   | 1001.4  |   1.788 |      60 |   32.57 |
| 2026-05-26    |    10 | 1020.88  |  995    |   2.601 |      50 |   31.94 |
| 2026-05-27    |    10 | 1009.04  |  983.56 |   2.591 |      50 |   27.61 |
| 2026-05-28    |    10 | 1003.85  |  961.18 |   4.439 |      60 |   27.32 |
| 2026-05-29    |    10 |  995.228 |  989.4  |   1.338 |      40 |   32.07 |
| 2026-06-01    |    10 |  993.822 |  983.58 |   1.453 |      50 |   29.29 |
| 2026-06-02    |    10 |  996.199 |  990.6  |   0.81  |      60 |   28.35 |

## Recent Volatile Targets

| origin_date   | target_date   |   horizon |   origin_close |   pred_close |   actual_close |   pred_delta |   actual_delta |   confidence |   ape_pct | dir_match   | direction_guard                | confidence_guard                                   | branch_name   |
|:--------------|:--------------|----------:|---------------:|-------------:|---------------:|-------------:|---------------:|-------------:|----------:|:------------|:-------------------------------|:---------------------------------------------------|:--------------|
| 2026-05-29    | 2026-06-01    |         1 |         989.4  |       988.39 |         983.58 |        -1.01 |          -5.82 |         34.2 |  0.48903  | True        | post_capitulation_rebound_fade | direction_guard_dampen|low_edge_confidence_dampen  | normal        |
| 2026-05-28    | 2026-06-01    |         2 |         961.18 |       964.78 |         983.58 |         3.6  |          22.4  |         68.6 |  1.91138  | True        | capitulation_rebound_release   | none                                               | jump          |
| 2026-05-27    | 2026-06-01    |         3 |         983.56 |       982.11 |         983.58 |        -1.45 |           0.02 |         22.7 |  0.149454 | False       | short_structure_guard          | direction_guard_dampen|low_edge_confidence_dampen  | trend_down    |
| 2026-05-26    | 2026-06-01    |         4 |         995    |      1012.16 |         983.58 |        17.16 |         -11.42 |         46.9 |  2.90571  | False       | none                           | none                                               | trend_down    |
| 2026-05-25    | 2026-06-01    |         5 |        1001.4  |      1003.25 |         983.58 |         1.85 |         -17.82 |         12.1 |  1.99984  | False       | low_confidence_decay           | direction_guard_dampen                             | trend_up      |
| 2026-05-22    | 2026-06-01    |         6 |         995.76 |       999.61 |         983.58 |         3.85 |         -12.18 |         23.9 |  1.62976  | False       | low_confidence_decay           | direction_guard_dampen                             | trend_up      |
| 2026-05-21    | 2026-06-01    |         7 |         995.38 |      1005.4  |         983.58 |        10.02 |         -11.8  |         21.4 |  2.21843  | False       | low_confidence_decay           | direction_guard_dampen                             | normal        |
| 2026-05-20    | 2026-06-01    |         8 |         986.64 |       984.95 |         983.58 |        -1.69 |          -3.06 |         21.7 |  0.139287 | True        | bearish_guard                  | direction_guard_dampen                             | trend_down    |
| 2026-05-19    | 2026-06-01    |         9 |        1002.18 |      1000.16 |         983.58 |        -2.02 |         -18.6  |         20.2 |  1.68568  | True        | bearish_guard                  | direction_guard_dampen                             | normal        |
| 2026-05-18    | 2026-06-01    |        10 |         999.8  |       997.41 |         983.58 |        -2.39 |         -16.22 |         21.2 |  1.40609  | True        | bearish_guard                  | direction_guard_dampen                             | trend_down    |
| 2026-06-01    | 2026-06-02    |         1 |         983.58 |       984.25 |         990.6  |         0.67 |           7.02 |         22.6 |  0.641026 | True        | cross_market_rebound_release   | direction_guard_dampen|tiny_edge_confidence_dampen | trend_down    |
| 2026-05-29    | 2026-06-02    |         2 |         989.4  |      1005    |         990.6  |        15.6  |           1.2  |         39.9 |  1.45366  | True        | none                           | whipsaw_confidence_dampen                          | normal        |
| 2026-05-28    | 2026-06-02    |         3 |         961.18 |       992.99 |         990.6  |        31.81 |          29.42 |         51.5 |  0.241268 | True        | none                           | none                                               |               |
| 2026-05-27    | 2026-06-02    |         4 |         983.56 |      1000.49 |         990.6  |        16.93 |           7.04 |         47.1 |  0.998385 | True        | none                           | none                                               | trend_down    |
| 2026-05-26    | 2026-06-02    |         5 |         995    |       993.73 |         990.6  |        -1.27 |          -4.4  |         29.7 |  0.31597  | True        | bearish_guard                  | direction_guard_dampen                             | trend_down    |
| 2026-05-25    | 2026-06-02    |         6 |        1001.4  |      1002.13 |         990.6  |         0.73 |         -10.8  |         10   |  1.16394  | False       | low_confidence_decay           | direction_guard_dampen|tiny_edge_confidence_dampen | trend_up      |
| 2026-05-22    | 2026-06-02    |         7 |         995.76 |       998.09 |         990.6  |         2.33 |          -5.16 |         20   |  0.756107 | False       | low_confidence_decay           | direction_guard_dampen                             | trend_up      |
| 2026-05-21    | 2026-06-02    |         8 |         995.38 |      1000.42 |         990.6  |         5.04 |          -4.78 |         21.4 |  0.991318 | False       | low_confidence_decay           | direction_guard_dampen                             | normal        |
| 2026-05-20    | 2026-06-02    |         9 |         986.64 |       984.84 |         990.6  |        -1.8  |           3.96 |         21.2 |  0.581466 | False       | bearish_guard                  | direction_guard_dampen                             | trend_down    |
| 2026-05-19    | 2026-06-02    |        10 |        1002.18 |      1000.05 |         990.6  |        -2.13 |         -11.58 |         20.1 |  0.953967 | True        | bearish_guard                  | direction_guard_dampen                             | normal        |
