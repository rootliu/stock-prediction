# Gold direct Scenario Report

- latest_date: 2026-04-10
- latest_close: 1048.36
- forecast_mode: direct

## 汇报版

- 最新基准: `2026-04-10` 收盘 `1048.36` 元/克
- 首日预测: `2026-04-13` 基础情景 `1053.69` 元/克，方向 `涨`，置信度 `41.6%`
- 波动区间: `1032.11 ~ 1075.27` 元/克
- 主 bullish 因子: 地缘风险 (1.00)
- 主 bearish 因子: 政策缓和预期 (0.98)
- 路径解释: 地缘风险新闻较密集，模型将其映射为短线风险溢价。

| date       |   bear_close |   base_close |   bull_close | direction   |   confidence | bull_driver   | bear_driver   |
|:-----------|-------------:|-------------:|-------------:|:------------|-------------:|:--------------|:--------------|
| 2026-04-13 |      1030.51 |      1053.69 |      1080.46 | 涨           |         41.6 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-14 |      1013.74 |      1054.67 |      1099.19 | 涨           |         37.9 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-15 |      1008.93 |      1060.23 |      1115.15 | 涨           |         45.8 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-16 |       991.16 |      1054.43 |      1117.7  | 涨           |         25.7 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-17 |       984.38 |      1047.21 |      1110.04 | 跌           |         25.7 | 地缘风险          | 模型中枢下方波动      |

![gold-direct-scenario](/Users/rootliu/code/report/gold_direct_scenario_2026-04-10.png)

### 调用说明

其它 agent 优先使用 wrapper 定时生成固定文件名的报告包：

```bash
/Users/rootliu/code/stock-prediction/scripts/run_gold_direct_report.sh /Users/rootliu/code/report <截止日期>
```

如果只需要原始动态命名产物，也可以直接调用：

```bash
cd /Users/rootliu/code/stock-prediction && .venv/bin/python run_gold_analysis.py --forecast-mode direct --skip-backtest --target-end <截止日期> --report-dir /Users/rootliu/code/report
```

推荐读取顺序：

1. 读取本 Markdown 作为汇报版正文
2. 读取同名 PNG 用于展示曲线图
3. 如需结构化数据，读取同名 CSV / JSON

## Forecast

| date       |   close | direction   |   confidence |   range_low |   range_high |
|:-----------|--------:|:------------|-------------:|------------:|-------------:|
| 2026-04-13 | 1053.69 | 涨           |         41.6 |     1032.11 |      1075.27 |
| 2026-04-14 | 1054.67 | 涨           |         37.9 |     1015.34 |      1093.99 |
| 2026-04-15 | 1060.23 | 涨           |         45.8 |     1010.54 |      1109.93 |
| 2026-04-16 | 1054.43 | 涨           |         25.7 |      992.04 |      1116.82 |
| 2026-04-17 | 1047.21 | 跌           |         25.7 |      967.61 |      1126.8  |

## Bull / Base / Bear

| date       |   bear_close |   base_low |   base_close |   base_high |   bull_close | bull_driver   | bear_driver   |
|:-----------|-------------:|-----------:|-------------:|------------:|-------------:|:--------------|:--------------|
| 2026-04-13 |      1030.51 |    1032.11 |      1053.69 |     1075.27 |      1080.46 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-14 |      1013.74 |    1015.34 |      1054.67 |     1093.99 |      1099.19 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-15 |      1008.93 |    1010.54 |      1060.23 |     1109.93 |      1115.15 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-16 |       991.16 |     992.04 |      1054.43 |     1116.82 |      1117.7  | 地缘风险          | 模型中枢下方波动      |
| 2026-04-17 |       984.38 |     967.61 |      1047.21 |     1126.8  |      1110.04 | 地缘风险          | 模型中枢下方波动      |

## Event Features

```json
{
  "news_bull_score": 0.9968,
  "news_bear_score": 0.8832,
  "blog_bull_score": 0.9709,
  "blog_bear_score": 0.8142,
  "article_count": 48,
  "safe_haven_score": 0.0,
  "policy_risk_score": 0.0,
  "geo_risk_score": 1.0,
  "sell_the_news_score": 0.0,
  "usd_pressure_score": 0.1295,
  "rate_pressure_score": 0.0,
  "oil_shock_score": 0.0,
  "structural_support_score": 0.0,
  "policy_relief_score": 0.982,
  "geo_relief_score": 0.9602
}
```

## Event Calibration

```json
{
  "median_abs_return": 0.013158,
  "p75_abs_return": 0.030607,
  "pre_event_scale": 0.008213,
  "post_event_scale": 0.006534,
  "sell_the_news_scale": 0.016906
}
```

## Key Headlines

| site          | published   | title                                                                                                  |
|:--------------|:------------|:-------------------------------------------------------------------------------------------------------|
| reuters.com   | 2026-04-11  | Americans weigh in on the Iran war, gas prices and their fears - Reuters                               |
| reuters.com   | 2026-04-11  | Exclusive: Iranian source says US has agreed to unfreeze Iranian funds, Washington denies it - Reuters |
| bloomberg.com | 2026-04-12  | US Hasn’t Reached Agreement With Iran, Vance Says - Bloomberg.com                                      |
| cnbc.com      | 2026-04-10  | Iran's speaker says negotiations with U.S. can't start without Lebanon ceasefire, asset release - CNBC |
| kitco.com     | 2026-04-10  | Gold extends three-week rally, but fragile ceasefire and inflation risks cap upside - KITCO            |
| fxstreet.com  | 2026-04-08  | DXY rebounds from 98.50 as ceasefire doubts mount - FXStreet                                           |

## Base Backtest

| 周期   |   样本数 |   MAE(元/克) |   RMSE(元/克) |   MAPE% |   方向准确率% |   平均信心度 |
|:-----|------:|-----------:|------------:|--------:|---------:|--------:|
| T+1  |    70 |       3.08 |        4.56 |    0.84 |     55.7 |    44.1 |
| T+2  |    70 |       5.45 |       10.12 |    1.35 |     45.7 |    41   |
| T+3  |    70 |       6.24 |       11.09 |    1.56 |     47.1 |    37.2 |
| T+4  |    70 |       7.34 |       14.67 |    1.72 |     54.3 |    35.8 |
| T+5  |    70 |       9.07 |       16.96 |    2.17 |     48.6 |    30.1 |

## Event Interval Backtest

| 周期   |   样本数 |   Base区间命中率% |   Event区间命中率% |   命中率改善% |   Base平均宽度% |   Event平均宽度% |
|:-----|------:|-------------:|--------------:|---------:|------------:|-------------:|
| T+1  |    70 |         57.1 |          57.1 |        0 |        1.66 |         1.67 |
| T+2  |    70 |         60   |          60   |        0 |        2.81 |         2.81 |
| T+3  |    70 |         74.3 |          74.3 |        0 |        3.96 |         3.96 |
| T+4  |    70 |         75.7 |          75.7 |        0 |        5.17 |         5.17 |
| T+5  |    70 |         74.3 |          74.3 |        0 |        6.42 |         6.27 |
