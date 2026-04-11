# Gold direct Scenario Report

- latest_date: 2026-04-08
- latest_close: 1062.00
- forecast_mode: direct

## 汇报版

- 最新基准: `2026-04-08` 收盘 `1062.00` 元/克
- 首日预测: `2026-04-09` 基础情景 `1052.64` 元/克，方向 `跌`，置信度 `57.7%`
- 波动区间: `1031.27 ~ 1074.01` 元/克
- 主 bullish 因子: 地缘风险 (1.00)
- 主 bearish 因子: 地缘缓和预期 (1.00)
- 路径解释: 地缘风险新闻较密集，模型将其映射为短线风险溢价。

| date       |   bear_close |   base_close |   bull_close | direction   |   confidence | bull_driver   | bear_driver   |
|:-----------|-------------:|-------------:|-------------:|:------------|-------------:|:--------------|:--------------|
| 2026-04-09 |      1029.72 |      1052.64 |      1079.79 | 跌           |         57.7 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-10 |      1012.22 |      1053.93 |      1100.27 | 跌           |         56.4 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-13 |       994.29 |      1045.32 |      1100.23 | 跌           |         52.2 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-14 |       981.27 |      1043.9  |      1106.53 | 跌           |         38.9 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-15 |       978.13 |      1040.56 |      1102.99 | 跌           |         39.1 | 地缘风险          | 模型中枢下方波动      |

![gold-direct-scenario](/Users/rootliu/code/report/gold_direct_scenario_2026-04-08.png)

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
| 2026-04-09 | 1052.64 | 跌           |         57.7 |     1031.27 |      1074.01 |
| 2026-04-10 | 1053.93 | 跌           |         56.4 |     1013.77 |      1094.1  |
| 2026-04-13 | 1045.32 | 跌           |         52.2 |      995.83 |      1094.82 |
| 2026-04-14 | 1043.9  | 跌           |         38.9 |      982.49 |      1105.32 |
| 2026-04-15 | 1040.56 | 跌           |         39.1 |      961.87 |      1119.26 |

## Bull / Base / Bear

| date       |   bear_close |   base_low |   base_close |   base_high |   bull_close | bull_driver   | bear_driver   |
|:-----------|-------------:|-----------:|-------------:|------------:|-------------:|:--------------|:--------------|
| 2026-04-09 |      1029.72 |    1031.27 |      1052.64 |     1074.01 |      1079.79 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-10 |      1012.22 |    1013.77 |      1053.93 |     1094.1  |      1100.27 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-13 |       994.29 |     995.83 |      1045.32 |     1094.82 |      1100.23 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-14 |       981.27 |     982.49 |      1043.9  |     1105.32 |      1106.53 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-15 |       978.13 |     961.87 |      1040.56 |     1119.26 |      1102.99 | 地缘风险          | 模型中枢下方波动      |

## Event Features

```json
{
  "news_bull_score": 0.9955,
  "news_bear_score": 0.9285,
  "blog_bull_score": 0.9538,
  "blog_bear_score": 0.9126,
  "article_count": 48,
  "safe_haven_score": 0.0,
  "policy_risk_score": 0.1974,
  "geo_risk_score": 1.0,
  "sell_the_news_score": 0.0,
  "usd_pressure_score": 0.0,
  "rate_pressure_score": 0.0,
  "oil_shock_score": 0.1088,
  "structural_support_score": 0.0,
  "policy_relief_score": 0.6423,
  "geo_relief_score": 0.9998
}
```

## Event Calibration

```json
{
  "median_abs_return": 0.012732,
  "p75_abs_return": 0.030607,
  "pre_event_scale": 0.008213,
  "post_event_scale": 0.007374,
  "sell_the_news_scale": 0.016906
}
```

## Key Headlines

| site          | published   | title                                                                                                         |
|:--------------|:------------|:--------------------------------------------------------------------------------------------------------------|
| cnbc.com      | 2026-04-09  | Inside India newsletter: Tariffs and Iran war threaten India's $100 billion garments export goal - CNBC       |
| reuters.com   | 2026-04-08  | Trump's abrupt Iran reversal exposes limits of his leverage - Reuters                                         |
| reuters.com   | 2026-04-08  | As Trump claims victory, Iran emerges bruised but powerful with leverage over Hormuz - Reuters                |
| reuters.com   | 2026-04-08  | Traders place large $950 million bet on oil price falling hours ahead of ceasefire - Reuters                  |
| investing.com | 2026-04-08  | Traders place large $950 million bet on oil price falling hours ahead of ceasefire By Reuters - Investing.com |
| fxstreet.com  | 2026-04-08  | Forex Today: FOMC Minutes reinforce 'higher-for-longer' as markets digest the ceasefire - FXStreet            |

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
