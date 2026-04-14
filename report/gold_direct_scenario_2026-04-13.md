# Gold direct Scenario Report

- latest_date: 2026-04-13
- latest_close: 1043.40
- forecast_mode: direct

## 汇报版

- 最新基准: `2026-04-13` 收盘 `1043.40` 元/克
- 首日预测: `2026-04-14` 基础情景 `1047.97` 元/克，方向 `涨`，置信度 `48.7%`
- 波动区间: `1026.20 ~ 1069.73` 元/克
- 主 bullish 因子: 地缘风险 (1.00)
- 主 bearish 因子: 政策缓和预期 (0.88)
- 路径解释: 地缘风险新闻较密集，模型将其映射为短线风险溢价。

| date       |   bear_close |   base_close |   bull_close | direction   |   confidence | bull_driver   | bear_driver   |
|:-----------|-------------:|-------------:|-------------:|:------------|-------------:|:--------------|:--------------|
| 2026-04-14 |      1024.4  |      1047.97 |      1075.14 | 涨           |         48.7 | 地缘风险          | 利率压力          |
| 2026-04-15 |      1014.26 |      1056.85 |      1103.09 | 涨           |         45.9 | 地缘风险          | 利率压力          |
| 2026-04-16 |      1003.94 |      1057.48 |      1114.66 | 涨           |         47   | 地缘风险          | 利率压力          |
| 2026-04-17 |       992.81 |      1056.18 |      1119.55 | 涨           |         28.1 | 地缘风险          | 利率压力          |

![gold-direct-scenario](/Users/rootliu/code/report/gold_direct_scenario_2026-04-13.png)

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
| 2026-04-14 | 1047.97 | 涨           |         48.7 |     1026.2  |      1069.73 |
| 2026-04-15 | 1056.85 | 涨           |         45.9 |     1016.08 |      1097.63 |
| 2026-04-16 | 1057.48 | 涨           |         47   |     1005.76 |      1109.2  |
| 2026-04-17 | 1056.18 | 涨           |         28.1 |      992.81 |      1119.56 |

## Bull / Base / Bear

| date       |   bear_close |   base_low |   base_close |   base_high |   bull_close | bull_driver   | bear_driver   |
|:-----------|-------------:|-----------:|-------------:|------------:|-------------:|:--------------|:--------------|
| 2026-04-14 |      1024.4  |    1026.2  |      1047.97 |     1069.73 |      1075.14 | 地缘风险          | 利率压力          |
| 2026-04-15 |      1014.26 |    1016.08 |      1056.85 |     1097.63 |      1103.09 | 地缘风险          | 利率压力          |
| 2026-04-16 |      1003.94 |    1005.76 |      1057.48 |     1109.2  |      1114.66 | 地缘风险          | 利率压力          |
| 2026-04-17 |       992.81 |     992.81 |      1056.18 |     1119.56 |      1119.55 | 地缘风险          | 利率压力          |

## Event Features

```json
{
  "news_bull_score": 0.9968,
  "news_bear_score": 0.6607,
  "blog_bull_score": 0.928,
  "blog_bear_score": 0.7403,
  "article_count": 48,
  "safe_haven_score": 0.0,
  "policy_risk_score": 0.1974,
  "geo_risk_score": 1.0,
  "sell_the_news_score": 0.0,
  "usd_pressure_score": 0.0,
  "rate_pressure_score": 0.4221,
  "oil_shock_score": 0.49,
  "structural_support_score": 0.0,
  "policy_relief_score": 0.8846,
  "geo_relief_score": 0.5966
}
```

## Event Calibration

```json
{
  "median_abs_return": 0.013158,
  "p75_abs_return": 0.030607,
  "pre_event_scale": 0.008201,
  "post_event_scale": 0.006534,
  "sell_the_news_scale": 0.016906
}
```

## Key Headlines

| site         | published   | title                                                                                          |
|:-------------|:------------|:-----------------------------------------------------------------------------------------------|
| cnbc.com     | 2026-04-13  | Trump threatens 50% tariffs on China as report suggests plans for arms shipment to Iran - CNBC |
| reuters.com  | 2026-04-13  | Morning Bid: Oil surges on US blockade of Iran - Reuters                                       |
| reuters.com  | 2026-04-13  | What does a US naval blockade of Iran mean for oil flows? - Reuters                            |
| cnbc.com     | 2026-04-13  | Treasury yields rise as collapse of Iran talks clouds inflation outlook - CNBC                 |
| fxstreet.com | 2026-04-13  | Gold builds on intraday ascent; hawkish Fed bets cap upside - FXStreet                         |
| kitco.com    | 2026-04-10  | Gold extends three-week rally, but fragile ceasefire and inflation risks cap upside - KITCO    |

## Base Backtest

| 周期   |   样本数 |   MAE(元/克) |   RMSE(元/克) |   MAPE% |   方向准确率% |   平均信心度 |
|:-----|------:|-----------:|------------:|--------:|---------:|--------:|
| T+1  |    71 |       3.05 |        4.53 |    0.83 |     56.3 |    44.1 |
| T+2  |    71 |       5.67 |       10.35 |    1.36 |     46.5 |    41.3 |
| T+3  |    71 |       6.19 |       11.02 |    1.54 |     47.9 |    37.5 |
| T+4  |    71 |       7.38 |       14.62 |    1.71 |     54.9 |    36   |
| T+5  |    71 |       9.08 |       16.88 |    2.16 |     49.3 |    30   |

## Event Interval Backtest

| 周期   |   样本数 |   Base区间命中率% |   Event区间命中率% |   命中率改善% |   Base平均宽度% |   Event平均宽度% |
|:-----|------:|-------------:|--------------:|---------:|------------:|-------------:|
| T+1  |    71 |         57.7 |          57.7 |        0 |        1.69 |         1.7  |
| T+2  |    71 |         60.6 |          60.6 |        0 |        2.87 |         2.87 |
| T+3  |    71 |         74.6 |          74.6 |        0 |        4.03 |         4.03 |
| T+4  |    71 |         76.1 |          76.1 |        0 |        5.27 |         5.27 |
| T+5  |    71 |         74.6 |          74.6 |        0 |        6.55 |         6.35 |
