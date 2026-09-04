# Gold direct Scenario Report

- latest_date: 2026-09-04
- latest_close: 965.96
- forecast_mode: direct

## 汇报版

- 最新基准: `2026-09-04` 收盘 `965.96` 元/克
- 首日预测: `2026-09-07` 基础情景 `957.40` 元/克，方向 `跌`，置信度 `55.1%`
- 波动区间: `950.72 ~ 964.08` 元/克
- 主 bullish 因子: 地缘风险 (1.00)
- 主 bearish 因子: 利率压力 (0.77)
- 路径解释: Event gating kept all horizons on base interval because history did not improve hit rate.
- 路径解释: Geopolitical risk is active and mainly widens the risk-premium scenario.

| date       | gate_mode   |   bear_close |   base_close |   bull_close | direction   |   confidence | bull_driver            | bear_driver            |
|:-----------|:------------|-------------:|-------------:|-------------:|:------------|-------------:|:-----------------------|:-----------------------|
| 2026-09-07 | base        |       950.72 |       957.4  |       964.08 | 跌           |         55.1 | base_interval_fallback | base_interval_fallback |
| 2026-09-08 | base        |       933.45 |       947.77 |       962.1  | 跌           |         62.1 | base_interval_fallback | base_interval_fallback |
| 2026-09-09 | base        |       921.94 |       945.74 |       969.55 | 跌           |         47   | base_interval_fallback | base_interval_fallback |

![gold-direct-scenario](/private/tmp/gold-direct-20260904-check/gold_direct_scenario_2026-09-04.png)

### 调用说明

其它 agent 优先使用 wrapper 定时生成固定文件名的报告包：

```bash
/Users/rootliu/code/stock-prediction/scripts/run_gold_direct_report.sh /private/tmp/gold-direct-20260904-check <截止日期>
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
| 2026-09-07 |  957.4  | 跌           |         55.1 |      950.72 |       964.08 |
| 2026-09-08 |  947.77 | 跌           |         62.1 |      933.45 |       962.1  |
| 2026-09-09 |  945.74 | 跌           |         47   |      921.94 |       969.55 |

## Bull / Base / Bear

| date       | gate_mode   |   bear_close |   base_low |   base_close |   base_high |   bull_close | bull_driver            | bear_driver            | gating_reason       |
|:-----------|:------------|-------------:|-----------:|-------------:|------------:|-------------:|:-----------------------|:-----------------------|:--------------------|
| 2026-09-07 | base        |       950.72 |     950.72 |       957.4  |      964.08 |       964.08 | base_interval_fallback | base_interval_fallback | no_backtest_history |
| 2026-09-08 | base        |       933.45 |     933.45 |       947.77 |      962.1  |       962.1  | base_interval_fallback | base_interval_fallback | no_backtest_history |
| 2026-09-09 | base        |       921.94 |     921.94 |       945.74 |      969.55 |       969.55 | base_interval_fallback | base_interval_fallback | no_backtest_history |

## Event Gating

```json
{
  "enabled": false,
  "reason": "no_backtest_history",
  "source": "historical_interval_hit_rate",
  "default_enabled": false,
  "min_improvement_pct": 0.0,
  "min_samples": 20,
  "enabled_horizons": [],
  "horizons": {}
}
```

## Event Features

```json
{
  "news_bull_score": 0.9824,
  "news_bear_score": 0.2259,
  "blog_bull_score": 0.7273,
  "blog_bear_score": 0.4995,
  "article_count": 44,
  "safe_haven_score": 0.0,
  "policy_risk_score": 0.5537,
  "geo_risk_score": 0.9999,
  "sell_the_news_score": 0.0,
  "usd_pressure_score": 0.0765,
  "rate_pressure_score": 0.7719,
  "oil_shock_score": 0.0674,
  "structural_support_score": 0.0,
  "policy_relief_score": 0.2125,
  "geo_relief_score": 0.0
}
```

## Event Calibration

```json
{
  "median_abs_return": 0.008163,
  "p75_abs_return": 0.018014,
  "pre_event_scale": 0.008201,
  "post_event_scale": 0.005635,
  "sell_the_news_scale": 0.016906
}
```

## Key Headlines

| site         | published   | title                                                                                                                            |
|:-------------|:------------|:---------------------------------------------------------------------------------------------------------------------------------|
| reuters.com  | 2026-09-04  | Oil rallies for the week as U.S.-Iran fighting resumes; diesel hits record high - Reuters                                        |
| reuters.com  | 2026-09-03  | US probes Iran wedding strike that analysis shows was likely direct hit by US munition - Reuters                                 |
| reuters.com  | 2026-09-03  | Deadly strike on Iranian wedding was likely a direct hit by a US munition, analysis shows - Reuters                              |
| cnbc.com     | 2026-09-04  | 2-year yield rises to highest since January 2025 after hot jobs report boosts expectations that the Fed could raise rates - CNBC |
| fxstreet.com | 2026-09-04  | Gold Price Forecast: Tempered hawkish Fed bets lift XAU/USD near $4,500 - FXStreet                                               |
| fxstreet.com | 2026-09-04  | British Pound strengthens above 1.3500 as BoE stays hawkish, traders brace for US NFP data - FXStreet                            |
