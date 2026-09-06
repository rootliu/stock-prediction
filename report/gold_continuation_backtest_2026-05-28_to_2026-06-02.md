# Gold Continuation Backtest (2026-05-28 to 2026-06-02)

- cutoff_date: 2026-05-28
- latest_trade_date: 2026-06-02
- latest_close: 990.60
- records: 30
- overall_direction_accuracy: 50.0%
- overall_confidence: 28.9
- note: variable-horizon evaluation includes partial latest targets, including T+1 into the latest trading day.

## Horizon Summary

| 周期   |   样本数 |   MAE(元/克) |   MAPE% |   方向准确率% |   平均信心度 |
|:-----|------:|-----------:|--------:|---------:|--------:|
| T+1  |     3 |      12.29 |    1.24 |    100   |    46.5 |
| T+2  |     3 |      13.41 |    1.36 |     66.7 |    44.2 |
| T+3  |     3 |       5.17 |    0.52 |     33.3 |    37   |
| T+4  |     3 |      11.61 |    1.18 |     33.3 |    29.5 |
| T+5  |     3 |      14.33 |    1.45 |     33.3 |    28.1 |
| T+6  |     3 |      14.76 |    1.49 |      0   |    19.6 |
| T+7  |     3 |      11.22 |    1.14 |      0   |    21.1 |
| T+8  |     3 |       7.36 |    0.74 |     66.7 |    21.3 |
| T+9  |     3 |      10.16 |    1.03 |     66.7 |    20.9 |
| T+10 |     3 |      11.98 |    1.21 |    100   |    20.9 |

## Bucket Summary

| 区间       |   样本数 |   MAPE% |   方向准确率% |   平均信心度 |
|:---------|------:|--------:|---------:|--------:|
| T+1~T+3  |     9 |    1.04 |     66.7 |    42.6 |
| T+4~T+5  |     6 |    1.32 |     33.3 |    28.8 |
| T+5~T+10 |    18 |    1.18 |     44.4 |    22   |

## By Target Date

| target_date   |   样本数 |   平均预测价 |   实际收盘 |   平均偏差率 |   方向准确率 |   平均信心度 |
|:--------------|------:|--------:|-------:|--------:|--------:|--------:|
| 2026-05-29    |    10 | 995.228 | 989.4  |   1.338 |      40 |   32.07 |
| 2026-06-01    |    10 | 992.878 | 983.58 |   1.357 |      50 |   27.79 |
| 2026-06-02    |    10 | 995.268 | 990.6  |   0.716 |      60 |   26.84 |

## Recent Volatile Targets

| origin_date   | target_date   |   horizon |   origin_close |   pred_close |   actual_close |   pred_delta |   actual_delta |   confidence |   ape_pct | dir_match   | direction_guard                | confidence_guard                                   | branch_name   |
|:--------------|:--------------|----------:|---------------:|-------------:|---------------:|-------------:|---------------:|-------------:|----------:|:------------|:-------------------------------|:---------------------------------------------------|:--------------|
| 2026-05-29    | 2026-06-01    |         1 |         989.4  |       988.39 |         983.58 |        -1.01 |          -5.82 |         34.2 |  0.48903  | True        | post_capitulation_rebound_fade | direction_guard_dampen|low_edge_confidence_dampen  | normal        |
| 2026-05-28    | 2026-06-01    |         2 |         961.18 |       964.78 |         983.58 |         3.6  |          22.4  |         68.6 |  1.91138  | True        | capitulation_rebound_release   | none                                               | jump          |
| 2026-05-27    | 2026-06-01    |         3 |         983.56 |       982.11 |         983.58 |        -1.45 |           0.02 |         22.7 |  0.149454 | False       | short_structure_guard          | direction_guard_dampen|low_edge_confidence_dampen  | trend_down    |
| 2026-05-26    | 2026-06-01    |         4 |         995    |      1002.72 |         983.58 |         7.72 |         -11.42 |         31.9 |  1.94595  | False       | mid_horizon_structure_decay    | direction_guard_dampen                             | trend_down    |
| 2026-05-25    | 2026-06-01    |         5 |        1001.4  |      1003.25 |         983.58 |         1.85 |         -17.82 |         12.1 |  1.99984  | False       | low_confidence_decay           | direction_guard_dampen                             | trend_up      |
| 2026-05-22    | 2026-06-01    |         6 |         995.76 |       999.61 |         983.58 |         3.85 |         -12.18 |         23.9 |  1.62976  | False       | low_confidence_decay           | direction_guard_dampen                             | trend_up      |
| 2026-05-21    | 2026-06-01    |         7 |         995.38 |      1005.4  |         983.58 |        10.02 |         -11.8  |         21.4 |  2.21843  | False       | low_confidence_decay           | direction_guard_dampen                             | normal        |
| 2026-05-20    | 2026-06-01    |         8 |         986.64 |       984.95 |         983.58 |        -1.69 |          -3.06 |         21.7 |  0.139287 | True        | bearish_guard                  | direction_guard_dampen                             | trend_down    |
| 2026-05-19    | 2026-06-01    |         9 |        1002.18 |      1000.16 |         983.58 |        -2.02 |         -18.6  |         20.2 |  1.68568  | True        | bearish_guard                  | direction_guard_dampen                             | normal        |
| 2026-05-18    | 2026-06-01    |        10 |         999.8  |       997.41 |         983.58 |        -2.39 |         -16.22 |         21.2 |  1.40609  | True        | bearish_guard                  | direction_guard_dampen                             | trend_down    |
| 2026-06-01    | 2026-06-02    |         1 |         983.58 |       984.25 |         990.6  |         0.67 |           7.02 |         22.6 |  0.641026 | True        | cross_market_rebound_release   | direction_guard_dampen|tiny_edge_confidence_dampen | trend_down    |
| 2026-05-29    | 2026-06-02    |         2 |         989.4  |      1005    |         990.6  |        15.6  |           1.2  |         39.9 |  1.45366  | True        | none                           | whipsaw_confidence_dampen                          | normal        |
| 2026-05-28    | 2026-06-02    |         3 |         961.18 |       992.99 |         990.6  |        31.81 |          29.42 |         51.5 |  0.241268 | True        | none                           | none                                               |               |
| 2026-05-27    | 2026-06-02    |         4 |         983.56 |       991.18 |         990.6  |         7.62 |           7.04 |         32   |  0.05855  | True        | mid_horizon_structure_decay    | direction_guard_dampen                             | trend_down    |
| 2026-05-26    | 2026-06-02    |         5 |         995    |       993.73 |         990.6  |        -1.27 |          -4.4  |         29.7 |  0.31597  | True        | bearish_guard                  | direction_guard_dampen                             | trend_down    |
| 2026-05-25    | 2026-06-02    |         6 |        1001.4  |      1002.13 |         990.6  |         0.73 |         -10.8  |         10   |  1.16394  | False       | low_confidence_decay           | direction_guard_dampen|tiny_edge_confidence_dampen | trend_up      |
| 2026-05-22    | 2026-06-02    |         7 |         995.76 |       998.09 |         990.6  |         2.33 |          -5.16 |         20   |  0.756107 | False       | low_confidence_decay           | direction_guard_dampen                             | trend_up      |
| 2026-05-21    | 2026-06-02    |         8 |         995.38 |      1000.42 |         990.6  |         5.04 |          -4.78 |         21.4 |  0.991318 | False       | low_confidence_decay           | direction_guard_dampen                             | normal        |
| 2026-05-20    | 2026-06-02    |         9 |         986.64 |       984.84 |         990.6  |        -1.8  |           3.96 |         21.2 |  0.581466 | False       | bearish_guard                  | direction_guard_dampen                             | trend_down    |
| 2026-05-19    | 2026-06-02    |        10 |        1002.18 |      1000.05 |         990.6  |        -2.13 |         -11.58 |         20.1 |  0.953967 | True        | bearish_guard                  | direction_guard_dampen                             | normal        |
