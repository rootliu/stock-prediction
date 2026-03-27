# 黄金实盘分钟级回测报告（2026-03-23）

## 1. 回测目标
- 使用实盘分时数据进行回测
- 回测窗口：`15分钟` 与 `30分钟`
- 日期范围：`2026-03-01` 到 `2026-03-23`
- 来源：`SHFE_AU_MAIN`（新浪分时，经 akshare）

## 2. 执行命令
```bash
/Users/rootliu/code/stock-prediction/.venv/bin/python \
  /Users/rootliu/code/stock-prediction/ml-service/backtest/gold_rolling_backtest.py \
  --source SHFE_AU_MAIN --period 15min --session ALL \
  --lookback 120 --max-horizon 8 --stride 2 \
  --start-date 2026-03-01 --end-date 2026-03-23 \
  --external-direction-csv /Users/rootliu/code/stock-prediction/ml-service/data/external_direction_signal.csv \
  --calibration-origin-cap 8 --output-dir /tmp/gold-backtest-15min-today

/Users/rootliu/code/stock-prediction/.venv/bin/python \
  /Users/rootliu/code/stock-prediction/ml-service/backtest/gold_rolling_backtest.py \
  --source SHFE_AU_MAIN --period 30min --session ALL \
  --lookback 120 --max-horizon 8 --stride 2 \
  --start-date 2026-03-01 --end-date 2026-03-23 \
  --external-direction-csv /Users/rootliu/code/stock-prediction/ml-service/data/external_direction_signal.csv \
  --calibration-origin-cap 8 --output-dir /tmp/gold-backtest-30min-today
```

## 3. 数据规模
| 周期 | raw_rows | origin_count | sample_count |
|---|---:|---:|---:|
| 15min | 580 | 226 | 3616 |
| 30min | 300 | 86 | 1376 |

## 4. 核心结果（boosting_external vs linear_baseline）

### 15min
| Horizon | Boosting MAPE | Linear MAPE | MAPE Delta | Boosting Direction Acc | Linear Direction Acc |
|---|---:|---:|---:|---:|---:|
| T+1 | 0.274% | 1.139% | -0.866 | 54.42% | 48.67% |
| T+2 | 0.423% | 1.440% | -1.017 | 52.21% | 49.12% |
| T+4 | 0.639% | 3.499% | -2.861 | 51.77% | 47.35% |
| T+8 | 0.984% | 5.714% | -4.730 | 59.73% | 48.23% |

### 30min
| Horizon | Boosting MAPE | Linear MAPE | MAPE Delta | Boosting Direction Acc | Linear Direction Acc |
|---|---:|---:|---:|---:|---:|
| T+1 | 0.404% | 1.256% | -0.852 | 41.86% | 54.65% |
| T+2 | 0.588% | 1.210% | -0.621 | 55.81% | 51.16% |
| T+4 | 1.013% | 2.568% | -1.556 | 54.65% | 59.30% |
| T+8 | 1.920% | 5.001% | -3.081 | 60.47% | 51.16% |

结论：
- 两个周期下，`boosting_external` 在幅度误差（MAPE）都显著优于线性基线。
- `30min` 的短期方向（T+1）出现退化，但到 T+8 又反超。

## 5. 今日样本（target_date=2026-03-23）
| 周期 | 模型 | 样本数 | 今日平均绝对误差 | 今日最大绝对误差 |
|---|---|---:|---:|---:|
| 15min | linear_baseline | 76 | 4.835% | 17.931% |
| 15min | boosting_external | 76 | 2.302% | 6.186% |
| 30min | linear_baseline | 36 | 6.921% | 19.638% |
| 30min | boosting_external | 36 | 3.497% | 10.279% |

## 6. 失真原因分析（分钟级）
1. 跨时段切换（白盘/夜盘）误差上升
- 15min：boosting 在 `DAY->NIGHT`、`NIGHT->DAY` 的 MAPE 高于同盘内预测。
- 30min：这种现象更明显，线性与 boosting 都在跨盘切换时变差。

2. 预测步长越长，误差越累积
- 15min boosting：MAPE 从 H1 `0.274%` 上升到 H8 `0.984%`。
- 30min boosting：MAPE 从 H1 `0.404%` 上升到 H8 `1.920%`。

3. 极端样本集中在夜盘到次日白盘过渡
- Top outlier 主要出现在 `2026-03-20` 和 `2026-03-23` 的跨盘窗口，说明分钟级跳变对递推链条冲击最大。

4. 30min 样本量更小，统计方差更高
- origin 数量：`86`（30min）显著少于 `226`（15min），造成方向指标更容易波动。

## 7. 改进建议
### P0（建议先做）
1. 跨盘门控：对 `DAY->NIGHT`/`NIGHT->DAY` 引入单独校准系数与更严格幅度剪裁。
2. 分时段建模：至少拆分 `DAY` 与 `NIGHT` 两个模型，再做加权融合。
3. 分周期参数：15min 与 30min 分开设置 `lookback/horizon/clip`，避免共用同一组超参。

### P1（第二阶段）
4. 事件特征增强：加入夜盘开盘前后虚拟变量、滚动成交量冲击特征。
5. 递推替换为 direct multi-horizon（H1~H8 独立头）降低误差传染。
6. 引入不确定度区间（P10/P50/P90），在跨盘窗口降低激进预测权重。

## 8. 回测产物
- `15min`：
  - `/tmp/gold-backtest-15min-today/backtest_summary.json`
  - `/tmp/gold-backtest-15min-today/backtest_detail.csv`
  - `/tmp/gold-backtest-15min-today/backtest_report.md`
- `30min`：
  - `/tmp/gold-backtest-30min-today/backtest_summary.json`
  - `/tmp/gold-backtest-30min-today/backtest_detail.csv`
  - `/tmp/gold-backtest-30min-today/backtest_report.md`
