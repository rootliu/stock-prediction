# Gold direct Scenario Report

- latest_date: 2026-03-30
- latest_close: 1014.88
- forecast_mode: direct

## Forecast

| date       |   close | direction   |   confidence |   range_low |   range_high |
|:-----------|--------:|:------------|-------------:|------------:|-------------:|
| 2026-03-31 | 1027.16 | 涨           |         75.4 |     1006.92 |      1047.39 |
| 2026-04-01 | 1028.68 | 涨           |         45   |      992.53 |      1064.83 |
| 2026-04-02 | 1025.31 | 涨           |         41.1 |      979.53 |      1071.08 |
| 2026-04-03 | 1034.86 | 涨           |         29.5 |      975.54 |      1094.19 |

## Bull / Base / Bear

| date       |   bear_close |   base_low |   base_close |   base_high |   bull_close | bull_driver   | bear_driver   |
|:-----------|-------------:|-----------:|-------------:|------------:|-------------:|:--------------|:--------------|
| 2026-03-31 |      1006.3  |    1006.92 |      1027.16 |     1047.39 |      1056.96 | 地缘风险、事件窗口前置   | 模型中枢下方波动      |
| 2026-04-01 |       990.67 |     992.53 |      1028.68 |     1064.83 |      1072.47 | 地缘风险、事件窗口前置   | 模型中枢下方波动      |
| 2026-04-02 |       977.94 |     979.53 |      1025.31 |     1071.08 |      1080.61 | 地缘风险、事件窗口前置   | 模型中枢下方波动      |
| 2026-04-03 |       972.77 |     975.54 |      1034.86 |     1094.19 |      1096.95 | 地缘风险          | 卖事实风险、事件落地回吐  |

## Event Features

```json
{
  "news_bull_score": 0.9952,
  "news_bear_score": 0.1823,
  "blog_bull_score": 0.9411,
  "blog_bear_score": 0.2559,
  "article_count": 48,
  "safe_haven_score": 0.0,
  "policy_risk_score": 0.0,
  "geo_risk_score": 1.0,
  "sell_the_news_score": 0.0,
  "usd_pressure_score": 0.0,
  "rate_pressure_score": 0.1295,
  "oil_shock_score": 0.2078,
  "structural_support_score": 0.0,
  "policy_relief_score": 0.4309,
  "geo_relief_score": 0.0
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

| site         | published   | title                                                                                                     |
|:-------------|:------------|:----------------------------------------------------------------------------------------------------------|
| reuters.com  | 2026-03-30  | US Defense Secretary Hegseth's broker looked to buy defense fund before Iran attack, FT reports - Reuters |
| reuters.com  | 2026-03-30  | Trump interested in calling on Arab states to help pay for Iran war, White House says - Reuters           |
| reuters.com  | 2026-03-30  | Fearing economic collapse after war, Iran cracks down on dissent - Reuters                                |
| fxstreet.com | 2026-03-30  | US Dollar Index (DXY) Forecast: Pulls back to 100 despite hawkish Fed - FXStreet                          |
| goldseek.com | 2026-03-23  | Gold Pares Dramatic Losses as Trump Backs Off From Iran Threat (Bloomberg) - goldseek.com                 |
| kitco.com    | 2026-03-30  | Gold pushes higher as dollar and oil surge, but key resistance looms - KITCO                              |
