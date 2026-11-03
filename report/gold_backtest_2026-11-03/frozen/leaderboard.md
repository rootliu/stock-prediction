# Gold version leaderboard

- rows: 20 (per version/horizon)
- champion: **v7** (least_worse_informative_model)
- champion mean skill: -0.0169
- directional edge: False

## Skill (1 - MAE / persistence MAE)

| version   |    T+1 |    T+3 |    T+5 |   T+10 |
|:----------|-------:|-------:|-------:|-------:|
| v0        |  0     |  0     |  0     |  0     |
| v1        | -0.166 | -0.105 | -0.054 | -0.041 |
| v3        | -0.05  | -0.042 | -0.027 | -0.016 |
| v4        | -0.024 | -0.02  | -0.016 | -0.007 |
| v7        | -0.024 | -0.016 | -0.011 | -0.002 |

## MAE (CNY/g)

| version   |   T+1 |   T+3 |   T+5 |   T+10 |
|:----------|------:|------:|------:|-------:|
| v0        | 10.31 | 19.6  | 26.42 |  31.85 |
| v1        | 12.01 | 21.66 | 27.84 |  33.15 |
| v3        | 10.83 | 20.43 | 27.13 |  32.37 |
| v4        | 10.56 | 20    | 26.84 |  32.08 |
| v7        | 10.56 | 19.91 | 26.7  |  31.91 |

## 80% interval coverage (walk-forward, causal)

| version   |   T+1 |   T+3 |   T+5 |   T+10 |
|:----------|------:|------:|------:|-------:|
| v0        | 0.864 | 0.836 | 0.667 |  0.488 |
| v1        | 0.848 | 0.782 | 0.608 |  0.463 |
| v3        | 0.848 | 0.8   | 0.647 |  0.488 |
| v4        | 0.848 | 0.818 | 0.628 |  0.488 |
| v7        | 0.848 | 0.818 | 0.628 |  0.463 |

## Direction audit

| version   |   horizon |   n |   direction_accuracy |   nonoverlap_n |   nonoverlap_direction_accuracy |   nonoverlap_direction_ci_low |   nonoverlap_direction_ci_high |
|:----------|----------:|----:|---------------------:|---------------:|--------------------------------:|------------------------------:|-------------------------------:|
| v0        |         1 |  69 |                 0    |             69 |                            0    |                          0    |                           5.27 |
| v1        |         1 |  69 |                50.72 |             69 |                           50.72 |                         39.21 |                          62.17 |
| v3        |         1 |  69 |                50.72 |             69 |                           50.72 |                         39.21 |                          62.17 |
| v4        |         1 |  69 |                50.72 |             69 |                           50.72 |                         39.21 |                          62.17 |
| v7        |         1 |  69 |                50.72 |             69 |                           50.72 |                         39.21 |                          62.17 |
| v0        |         3 |  67 |                 0    |             23 |                            0    |                          0    |                          14.31 |
| v1        |         3 |  67 |                52.24 |             23 |                           52.17 |                         32.96 |                          70.76 |
| v3        |         3 |  67 |                52.24 |             23 |                           52.17 |                         32.96 |                          70.76 |
| v4        |         3 |  67 |                52.24 |             23 |                           52.17 |                         32.96 |                          70.76 |
| v7        |         3 |  67 |                52.24 |             23 |                           52.17 |                         32.96 |                          70.76 |
| v0        |         5 |  65 |                 0    |             13 |                            0    |                          0    |                          22.81 |
| v1        |         5 |  65 |                44.62 |             13 |                           61.54 |                         35.52 |                          82.29 |
| v3        |         5 |  65 |                44.62 |             13 |                           61.54 |                         35.52 |                          82.29 |
| v4        |         5 |  65 |                44.62 |             13 |                           61.54 |                         35.52 |                          82.29 |
| v7        |         5 |  65 |                44.62 |             13 |                           61.54 |                         35.52 |                          82.29 |
| v0        |        10 |  60 |                 0    |              6 |                            0    |                          0    |                          39.03 |
| v1        |        10 |  60 |                41.67 |              6 |                           50    |                         18.76 |                          81.24 |
| v3        |        10 |  60 |                41.67 |              6 |                           50    |                         18.76 |                          81.24 |
| v4        |        10 |  60 |                41.67 |              6 |                           50    |                         18.76 |                          81.24 |
| v7        |        10 |  60 |                41.67 |              6 |                           50    |                         18.76 |                          81.24 |

Non-overlapping intervals are selected separately per horizon before scoring. They reduce overlap, not all market dependence; CI is 95% Wilson. Fewer than 30 selected samples cannot support a direction-edge claim.

## Decision

- v1: rejected — mean skill -0.108 < -0.02
- v3: rejected — mean skill -0.040 < -0.02
- v4: rejected — mean skill -0.020 < -0.02
- v7: eligible (mean skill -0.017)
- v7: insufficient non-overlapping direction evidence; do not claim an edge
- v7: descriptive T+1/T+3/T+5 mean skill -0.017; selection on this evaluation set is not independent validation
- not better than a flat forecast; allowed only by the configured tolerance

Selection requires all T+1/3/5/10 horizons, n >= 40, and T+1/3 coverage in [0.72, 0.88].
Rank by mean skill at T+1/3/5; default tolerance is -0.02. Negative skill is not an edge.
Direction is disclosed, not a promotion gate. Overlapping-row Wilson intervals are descriptive only.