# Gold Continuation Backtest (2026-05-28 to 2026-06-12)

- cutoff_date: 2026-05-28
- latest_trade_date: 2026-06-12
- latest_close: 911.62
- records: 110
- overall_direction_accuracy: 55.45%
- overall_confidence: 27.51
- note: variable-horizon evaluation includes partial latest targets, including T+1 into the latest trading day.

## Horizon Summary

| 周期   |   样本数 |   MAE(元/克) |   MAPE% |   方向准确率% |   平均信心度 |
|:-----|------:|-----------:|--------:|---------:|--------:|
| T+1  |    11 |       9.86 |    1.03 |     81.8 |    47.9 |
| T+2  |    11 |      18.02 |    1.92 |     63.6 |    38.5 |
| T+3  |    11 |      21.52 |    2.3  |     45.5 |    33.3 |
| T+4  |    11 |      30.27 |    3.24 |     45.5 |    30   |
| T+5  |    11 |      32.96 |    3.53 |     54.5 |    25.4 |
| T+6  |    11 |      34.96 |    3.76 |     45.5 |    21.8 |
| T+7  |    11 |      34.06 |    3.67 |     45.5 |    20.8 |
| T+8  |    11 |      34.7  |    3.74 |     54.5 |    19.2 |
| T+9  |    11 |      36.52 |    3.92 |     54.5 |    19   |
| T+10 |    11 |      37.77 |    4.05 |     63.6 |    19.2 |

## Bucket Summary

| 区间       |   样本数 |   MAPE% |   方向准确率% |   平均信心度 |
|:---------|------:|--------:|---------:|--------:|
| T+1~T+3  |    33 |    1.75 |     63.6 |    39.9 |
| T+4~T+5  |    22 |    3.39 |     50   |    27.7 |
| T+5~T+10 |    66 |    3.78 |     53   |    20.9 |

## By Target Date

| target_date   |   样本数 |   平均预测价 |   实际收盘 |   平均偏差率 |   方向准确率 |   平均信心度 |
|:--------------|------:|--------:|-------:|--------:|--------:|--------:|
| 2026-05-29    |    10 | 995.228 | 989.4  |   1.338 |      40 |   32.07 |
| 2026-06-01    |    10 | 992.878 | 983.58 |   1.357 |      50 |   27.79 |
| 2026-06-02    |    10 | 995.268 | 990.6  |   0.716 |      60 |   26.84 |
| 2026-06-03    |    10 | 992.489 | 977.08 |   1.577 |      50 |   27.7  |
| 2026-06-04    |    10 | 987.905 | 977.94 |   1.449 |      40 |   24.87 |
| 2026-06-05    |    10 | 986.802 | 974.02 |   1.607 |      30 |   20.6  |
| 2026-06-08    |    10 | 982.6   | 942.2  |   4.288 |      60 |   26.36 |
| 2026-06-09    |    10 | 979.196 | 947.04 |   3.395 |      60 |   29.13 |
| 2026-06-10    |    10 | 971.976 | 919.32 |   5.728 |      60 |   33.97 |
| 2026-06-11    |    10 | 962.23  | 895    |   7.512 |      80 |   27.17 |
| 2026-06-12    |    10 | 958.95  | 911.62 |   5.305 |      80 |   26.09 |

## Recent Volatile Targets

| origin_date   | target_date   |   horizon |   origin_close |   pred_close |   actual_close |   pred_delta |   actual_delta |   confidence |   ape_pct | dir_match   | direction_guard              | confidence_guard                                  | branch_name   |
|:--------------|:--------------|----------:|---------------:|-------------:|---------------:|-------------:|---------------:|-------------:|----------:|:------------|:-----------------------------|:--------------------------------------------------|:--------------|
| 2026-06-10    | 2026-06-11    |         1 |         919.32 |       905.87 |         895    |       -13.45 |         -24.32 |         40.1 |  1.21453  | True        | none                         | none                                              | trend_down    |
| 2026-06-09    | 2026-06-11    |         2 |         947.04 |       939.5  |         895    |        -7.54 |         -52.04 |         63.6 |  4.97207  | True        | none                         | none                                              | normal        |
| 2026-06-08    | 2026-06-11    |         3 |         942.2  |       940.81 |         895    |        -1.39 |         -47.2  |         12.2 |  5.11844  | True        | near_breakdown_guard         | direction_guard_dampen|low_edge_confidence_dampen | trend_down    |
| 2026-06-05    | 2026-06-11    |         4 |         974.02 |       955.76 |         895    |       -18.26 |         -79.02 |         27.2 |  6.78883  | True        | none                         | none                                              |               |
| 2026-06-04    | 2026-06-11    |         5 |         977.94 |       976.69 |         895    |        -1.25 |         -82.94 |         28.4 |  9.12737  | True        | bearish_guard                | direction_guard_dampen                            | trend_up      |
| 2026-06-03    | 2026-06-11    |         6 |         977.08 |       975.72 |         895    |        -1.36 |         -82.08 |         24.5 |  9.01899  | True        | bearish_guard                | direction_guard_dampen                            | trend_down    |
| 2026-06-02    | 2026-06-11    |         7 |         990.6  |       993.86 |         895    |         3.26 |         -95.6  |         21.9 | 11.0458   | False       | low_confidence_decay         | direction_guard_dampen                            | trend_up      |
| 2026-06-01    | 2026-06-11    |         8 |         983.58 |       981.99 |         895    |        -1.59 |         -88.58 |         22.3 |  9.71955  | True        | bearish_guard                | direction_guard_dampen                            | trend_down    |
| 2026-05-29    | 2026-06-11    |         9 |         989.4  |       992.89 |         895    |         3.49 |         -94.4  |         12   | 10.9374   | False       | low_confidence_decay         | whipsaw_confidence_dampen|direction_guard_dampen  | normal        |
| 2026-05-28    | 2026-06-11    |        10 |         961.18 |       959.21 |         895    |        -1.97 |         -66.18 |         19.5 |  7.1743   | True        | bearish_guard                | direction_guard_dampen                            |               |
| 2026-06-11    | 2026-06-12    |         1 |         895    |       906.48 |         911.62 |        11.48 |          16.62 |         57.4 |  0.563831 | True        | capitulation_rebound_release | none                                              | trend_down    |
| 2026-06-10    | 2026-06-12    |         2 |         919.32 |       918.21 |         911.62 |        -1.11 |          -7.7  |         10.3 |  0.722889 | True        | short_structure_guard        | direction_guard_dampen|low_edge_confidence_dampen | trend_down    |
| 2026-06-09    | 2026-06-12    |         3 |         947.04 |       939.06 |         911.62 |        -7.98 |         -35.42 |         49.9 |  3.01003  | True        | none                         | none                                              | normal        |
| 2026-06-08    | 2026-06-12    |         4 |         942.2  |       940.41 |         911.62 |        -1.79 |         -30.58 |         18.4 |  3.15811  | True        | mid_horizon_breakdown_guard  | direction_guard_dampen                            | trend_down    |
| 2026-06-05    | 2026-06-12    |         5 |         974.02 |       961.57 |         911.62 |       -12.45 |         -62.4  |         23   |  5.47926  | True        | none                         | none                                              |               |
| 2026-06-04    | 2026-06-12    |         6 |         977.94 |       976.57 |         911.62 |        -1.37 |         -66.32 |         24.3 |  7.12468  | True        | bearish_guard                | direction_guard_dampen                            | trend_up      |
| 2026-06-03    | 2026-06-12    |         7 |         977.08 |       975.61 |         911.62 |        -1.47 |         -65.46 |         22   |  7.01937  | True        | bearish_guard                | direction_guard_dampen                            | trend_down    |
| 2026-06-02    | 2026-06-12    |         8 |         990.6  |       994.34 |         911.62 |         3.74 |         -78.98 |         21.4 |  9.07396  | False       | low_confidence_decay         | direction_guard_dampen                            | trend_up      |
| 2026-06-01    | 2026-06-12    |         9 |         983.58 |       981.9  |         911.62 |        -1.68 |         -71.96 |         22.2 |  7.70935  | True        | bearish_guard                | direction_guard_dampen                            | trend_down    |
| 2026-05-29    | 2026-06-12    |        10 |         989.4  |       995.35 |         911.62 |         5.95 |         -77.78 |         12   |  9.18475  | False       | low_confidence_decay         | whipsaw_confidence_dampen|direction_guard_dampen  | normal        |
