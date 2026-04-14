# Gold direct Scenario Report

- latest_date: 2026-03-31
- latest_close: 1020.10
- forecast_mode: direct

## 汇报版

- 最新基准: `2026-03-31` 收盘 `1020.10` 元/克
- 首日预测: `2026-04-01` 基础情景 `1034.52` 元/克，方向 `涨`，置信度 `82.9%`
- 波动区间: `1014.71 ~ 1054.33` 元/克
- 主 bullish 因子: 地缘风险 (1.00)
- 主 bearish 因子: 地缘缓和预期 (0.14)
- 路径解释: 地缘风险新闻较密集，模型将其映射为短线风险溢价。

| date       |   bear_close |   base_close |   bull_close | direction   |   confidence | bull_driver   | bear_driver   |
|:-----------|-------------:|-------------:|-------------:|:------------|-------------:|:--------------|:--------------|
| 2026-04-01 |      1013.09 |      1034.52 |      1062.09 | 涨           |         82.9 | 地缘风险、事件窗口前置   | 模型中枢下方波动      |
| 2026-04-02 |       995.63 |      1033.66 |      1080.01 | 涨           |         62.3 | 地缘风险、事件窗口前置   | 模型中枢下方波动      |
| 2026-04-03 |       974.87 |      1034.15 |      1086.52 | 涨           |         52.8 | 地缘风险          | 卖事实风险、事件落地回吐  |

![gold-direct-scenario](/Users/rootliu/code/report/gold_direct_scenario_2026-03-31.png)

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
| 2026-04-01 | 1034.52 | 涨           |         82.9 |     1014.71 |      1054.33 |
| 2026-04-02 | 1033.66 | 涨           |         62.3 |      996.99 |      1070.34 |
| 2026-04-03 | 1034.15 | 涨           |         52.8 |      987.13 |      1081.16 |

## Bull / Base / Bear

| date       |   bear_close |   base_low |   base_close |   base_high |   bull_close | bull_driver   | bear_driver   |
|:-----------|-------------:|-----------:|-------------:|------------:|-------------:|:--------------|:--------------|
| 2026-04-01 |      1013.09 |    1014.71 |      1034.52 |     1054.33 |      1062.09 | 地缘风险、事件窗口前置   | 模型中枢下方波动      |
| 2026-04-02 |       995.63 |     996.99 |      1033.66 |     1070.34 |      1080.01 | 地缘风险、事件窗口前置   | 模型中枢下方波动      |
| 2026-04-03 |       974.87 |     987.13 |      1034.15 |     1081.16 |      1086.52 | 地缘风险          | 卖事实风险、事件落地回吐  |

## Event Features

```json
{
  "news_bull_score": 0.9958,
  "news_bear_score": 0.0,
  "blog_bull_score": 0.9516,
  "blog_bear_score": 0.162,
  "article_count": 48,
  "safe_haven_score": 0.0523,
  "policy_risk_score": 0.0,
  "geo_risk_score": 1.0,
  "sell_the_news_score": 0.0,
  "usd_pressure_score": 0.1295,
  "rate_pressure_score": 0.0,
  "oil_shock_score": 0.0,
  "structural_support_score": 0.0,
  "policy_relief_score": 0.0731,
  "geo_relief_score": 0.1437
}
```

## Event Calibration

```json
{
  "median_abs_return": 0.012695,
  "p75_abs_return": 0.026929,
  "pre_event_scale": 0.008533,
  "post_event_scale": 0.005635,
  "sell_the_news_scale": 0.016906
}
```

## Key Headlines

| site         | published   | title                                                                                                                                                             |
|:-------------|:------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| reuters.com  | 2026-03-31  | Trump says the US could end the Iran war in two to three weeks - Reuters                                                                                          |
| reuters.com  | 2026-03-31  | Trump says U.S. could end Iran war in two to three weeks - Reuters                                                                                                |
| reuters.com  | 2026-03-31  | Two-thirds of Americans want quick end to Iran war even if goals unachieved, Reuters/Ipsos poll finds - Reuters                                                   |
| fxstreet.com | 2026-03-31  | Gold holds above $4,550 as USD eases on Iran ceasefire hopes - FXStreet                                                                                           |
| kitco.com    | 2026-03-24  | Precious metals selloff reflects Iran liquidity crunch, and the gold outlook could improve ‘quite sharply’ once forced selling stops – Saxo Bank’s Hansen - KITCO |
| goldseek.com | 2026-03-25  | Gold & Silver Surge on US-Iran 15-Point Peace Plan News - goldseek.com                                                                                            |

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
