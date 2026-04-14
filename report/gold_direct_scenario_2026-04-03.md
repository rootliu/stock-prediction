# Gold direct Scenario Report

- latest_date: 2026-04-03
- latest_close: 1033.00
- forecast_mode: direct

## 汇报版

- 最新基准: `2026-04-03` 收盘 `1033.00` 元/克
- 首日预测: `2026-04-06` 基础情景 `1035.73` 元/克，方向 `涨`，置信度 `40.6%`
- 波动区间: `1015.06 ~ 1056.41` 元/克
- 主 bullish 因子: 地缘风险 (1.00)
- 主 bearish 因子: 地缘缓和预期 (0.81)
- 路径解释: 地缘风险新闻较密集，模型将其映射为短线风险溢价。

| date       |   bear_close |   base_close |   bull_close | direction   |   confidence | bull_driver   | bear_driver   |
|:-----------|-------------:|-------------:|-------------:|:------------|-------------:|:--------------|:--------------|
| 2026-04-06 |      1011.43 |      1035.73 |      1061.65 | 涨           |         40.6 | 地缘风险          | 事件落地回吐        |
| 2026-04-07 |       999.13 |      1041.08 |      1085.26 | 涨           |         56.7 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-08 |       993.6  |      1043.73 |      1098.01 | 涨           |         57.1 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-09 |       975.28 |      1037.53 |      1099.78 | 涨           |         50.3 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-10 |       971.53 |      1033.54 |      1095.55 | 涨           |         19.6 | 地缘风险          | 模型中枢下方波动      |

![gold-direct-scenario](/Users/rootliu/code/report/gold_direct_scenario_2026-04-03.png)

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
| 2026-04-06 | 1035.73 | 涨           |         40.6 |     1015.06 |      1056.41 |
| 2026-04-07 | 1041.08 | 涨           |         56.7 |     1002.17 |      1079.99 |
| 2026-04-08 | 1043.73 | 涨           |         57.1 |      994.89 |      1092.57 |
| 2026-04-09 | 1037.53 | 涨           |         50.3 |      975.43 |      1099.64 |
| 2026-04-10 | 1033.54 | 涨           |         19.6 |      953.93 |      1113.16 |

## Bull / Base / Bear

| date       |   bear_close |   base_low |   base_close |   base_high |   bull_close | bull_driver   | bear_driver   |
|:-----------|-------------:|-----------:|-------------:|------------:|-------------:|:--------------|:--------------|
| 2026-04-06 |      1011.43 |    1015.06 |      1035.73 |     1056.41 |      1061.65 | 地缘风险          | 事件落地回吐        |
| 2026-04-07 |       999.13 |    1002.17 |      1041.08 |     1079.99 |      1085.26 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-08 |       993.6  |     994.89 |      1043.73 |     1092.57 |      1098.01 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-09 |       975.28 |     975.43 |      1037.53 |     1099.64 |      1099.78 | 地缘风险          | 模型中枢下方波动      |
| 2026-04-10 |       971.53 |     953.93 |      1033.54 |     1113.16 |      1095.55 | 地缘风险          | 模型中枢下方波动      |

## Event Features

```json
{
  "news_bull_score": 0.9966,
  "news_bear_score": 0.3774,
  "blog_bull_score": 0.9729,
  "blog_bear_score": 0.7435,
  "article_count": 48,
  "safe_haven_score": 0.0,
  "policy_risk_score": 0.108,
  "geo_risk_score": 1.0,
  "sell_the_news_score": 0.0,
  "usd_pressure_score": 0.0,
  "rate_pressure_score": 0.1295,
  "oil_shock_score": 0.2797,
  "structural_support_score": 0.0,
  "policy_relief_score": 0.5588,
  "geo_relief_score": 0.8137
}
```

## Event Calibration

```json
{
  "median_abs_return": 0.012732,
  "p75_abs_return": 0.030607,
  "pre_event_scale": 0.008213,
  "post_event_scale": 0.005635,
  "sell_the_news_scale": 0.016906
}
```

## Key Headlines

| site          | published   | title                                                                                        |
|:--------------|:------------|:---------------------------------------------------------------------------------------------|
| reuters.com   | 2026-04-07  | Stocks struggle, oil jumps as Trump's Iran deadline looms - reuters.com                      |
| reuters.com   | 2026-04-06  | Oil prices extend gains as Trump sharpens rhetoric on Iran - reuters.com                     |
| reuters.com   | 2026-04-06  | Trump seizes on rescue of downed airman to recast unpopular Iran war - reuters.com           |
| fxstreet.com  | 2026-04-07  | Gold remains depressed as Hormuz standoff supports USD amid hawkish Fed rate bets - FXStreet |
| investing.com | 2026-04-06  | Asia stocks: Nikkei, KOSPI rise over 1% on report of Iran ceasefire talks - investing.com    |
| kitco.com     | 2026-04-02  | Indian dealers charge first gold premiums in two months - KITCO                              |

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
