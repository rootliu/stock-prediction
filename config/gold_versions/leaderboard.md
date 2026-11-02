# Gold version leaderboard

- rows: 20 (per version/horizon)
- champion: **v7** (least_worse_informative_model)
- champion mean skill: -0.0131
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

## Decision

- v1: rejected — mean skill -0.091 < -0.02
- v3: rejected — mean skill -0.034 < -0.02
- v4: eligible (mean skill -0.017)
- v7: eligible (mean skill -0.013)
- v7: direction CI low 30.1% < 50% -> no directional edge; report must not claim one
- v7: promoted, but skill -0.013 means it is NOT better than a flat forecast; deploy as 'least-worse informative model', disclose the negative skill

Selection rule is pre-registered: gate on direction CI, then mean skill > 0.
If every model version is negative, the champion is v0 (persistence).