# Gold Price Forecast Tool / 黄金价格预测工具

## 概述

基于机器学习的黄金价格每日预测工具，输出统一为 **人民币/克 (CNY/g)**，显示每日 16:00 收盘预测价。

### 核心特性

- **多数据源**: SHFE 上期所黄金主力合约 (默认) 或 COMEX 纽约黄金期货
- **跨市场信号**: 自动融合 DXY 美元指数、VIX 恐慌指数、US10Y 美国国债收益率、USDCNY 汇率、内外盘价差
- **逐日独立预测**: 每天 horizon=1 独立训练预测，消除递归误差累积
- **三模型自适应融合**: Linear / GradientBoosting / Ensemble 按实时准确率动态加权
- **极端行情过滤**: 近 5 日收益率超 2 倍标准差时自动触发均值回归压缩
- **统一输出**: CNY/克，每天一行

---

## 快速开始

```bash
# 默认模式: SHFE AU, 含回测 + 预测 (~2-3 分钟)
python run_gold_analysis.py

# 快速预测: 跳过回测 (~30 秒)
python run_gold_analysis.py --skip-backtest

# 极速模式: 跳过回测和跨市场信号 (~20 秒)
python run_gold_analysis.py --skip-backtest --skip-cross-market
```

---

## 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--source` | `shfe` | 数据源: `shfe` = 上期所黄金主力合约, `comex` = COMEX GC=F (自动转 CNY/克) |
| `--target-end` | `2026-04-03` | 预测截止日期 (YYYY-MM-DD) |
| `--lookback` | `240` | 模型训练窗口大小 (天数) |
| `--backtest-stride` | `10` | 回测步长 (越小越精确但越慢) |
| `--backtest-horizon` | `5` | 回测最大预测天数 |
| `--skip-backtest` | `false` | 跳过回测，仅输出预测 |
| `--skip-cross-market` | `false` | 跳过跨市场信号调整 |

---

## Agent / Cron 调用指南

### 作为 Python 函数调用

```python
from run_gold_analysis import main

# 默认调用
forecast_df = main()

# 自定义参数
forecast_df = main(
    source="shfe",           # 或 "comex"
    target_end="2026-04-10", # 预测到4月10日
    lookback=240,
    skip_backtest=True,      # 快速模式
    skip_cross_market=False,
)
# forecast_df 是 pandas DataFrame，包含 date, close, direction, confidence 列
```

### 作为 CLI 工具调用 (cron / 定时任务)

```bash
# 每日 cron 任务: 快速预测未来5个交易日
python run_gold_analysis.py --skip-backtest --target-end $(date -d "+7 days" +%Y-%m-%d)

# 每周末完整回测 + 预测
python run_gold_analysis.py --backtest-stride 5 --target-end $(date -d "+14 days" +%Y-%m-%d)
```

### Agent 调用场景

| 用户指令 | 对应命令 |
|---------|---------|
| "看看明天金价" | `python run_gold_analysis.py --skip-backtest --target-end <明天日期>` |
| "预测下周金价" | `python run_gold_analysis.py --skip-backtest --target-end <下周五日期>` |
| "跑个完整回测看看准不准" | `python run_gold_analysis.py --backtest-stride 5` |
| "用 COMEX 数据预测" | `python run_gold_analysis.py --source comex --skip-backtest` |
| "预测到月底" | `python run_gold_analysis.py --target-end <月底日期>` |
| "快速预测不要回测" | `python run_gold_analysis.py --skip-backtest --skip-cross-market` |

---

## 输出格式

```
日期          预测16:00收盘(元/克)  方向  较前日涨跌(元/克)  信心度
------------------------------------------------------------------------
2026-03-27                998.50    涨              +2.52   72.5%
2026-03-28                995.30    跌              -3.20   58.2%
2026-03-31               1001.10    涨              +5.80   65.0%
2026-04-01                999.80    跌              -1.30   51.2%
2026-04-02               1003.20    涨              +3.40   68.8%
2026-04-03               1005.60    涨              +2.40   62.5%
```

- **方向**: 涨/跌/平
- **信心度**: 0-100%，基于模型投票一致性和方向概率

---

## 模型架构

```
SHFE AU (CNY/克)  ─┐
                   ├─ 跨市场调整 ─→ adjusted_close
COMEX (USD/oz)    ─┤    (DXY, VIX, US10Y, 内外盘价差)
USDCNY            ─┤
DXY / VIX / US10Y ─┘
                           │
                  ┌────────┴────────┐
                  │  逐日 horizon=1  │
                  │  预测循环        │
                  └────────┬────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         Linear Reg    Boosting    Ensemble
              │            │            │
              └────────────┼────────────┘
                           │
                  自适应加权合并
                  (MAPE + 方向准确率)
                           │
                  极端行情过滤
                  (5日收益率 > 2σ → 压缩40%)
                           │
                    最终预测 (CNY/克)
```

---

## 依赖

```
akshare>=1.12.0
yfinance>=0.2.0
scikit-learn>=1.4.0
pandas>=2.1.0
numpy>=1.26.0
```

---

## 单位换算参考

| 换算 | 公式 |
|------|------|
| COMEX (USD/oz) → CNY/克 | `USD价格 * USDCNY汇率 / 31.1035` |
| 1 金衡盎司 (troy oz) | 31.1035 克 |
| SHFE AU | 已经是 CNY/克，无需换算 |
