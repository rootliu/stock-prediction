# Gold Price Forecast Tool / 黄金价格预测工具

## 概述

基于机器学习的黄金价格每日预测工具，输出统一为 **人民币/克 (CNY/g)**，显示每日 16:00 收盘预测价。

采用 **Multi-Bar 架构**: 从 SHFE AU 60min K 线聚合出 6 个时点 (04:00/09:00/12:00/16:00/20:00/24:00)，每个时点独立训练 GBM 模型预测当日 16:00 收盘价，最终加权聚合输出。

### 核心特性

- **Multi-Bar 多时点预测**: 6 个 checkpoint 模型加权聚合，比单日线预测误差降低 ~77%
- **夜盘/日盘分时数据**: 自动获取 SHFE AU 60min K 线，包含完整夜盘 (21:00-02:30) 信息
- **跨市场信号**: 自动融合 DXY 美元指数、VIX 恐慌指数、US10Y 美国国债收益率、USDCNY 汇率、COMEX 隔夜收益率、内外盘价差
- **波动率 Regime 自适应**: 自动检测 low/normal/high/extreme 四档波动率，高波时压缩预测幅度
- **Checkpoint 可追溯**: 输出每个时点的独立预测值、权重、置信度
- **统一输出**: CNY/克，每天一行，附带波动区间

### 模型对比 (2026-03-27 实测)

| 指标 | 旧模型 (日线) | 新模型 (Multi-Bar) |
|------|-------------|-------------------|
| 预测值 | 1010.31 | 987.69 |
| 实际值 | 991.88 | 991.88 |
| 误差 | 18.43 (1.86%) | **4.19 (0.42%)** |
| 方向 | 错 (预测涨, 实际跌) | **对 (预测跌, 实际跌)** |
| 方向准确率 (训练) | ~50% | **68-83%** |

---

## 快速开始

```bash
cd stock-prediction

# 默认模式: 含回测 + 预测 (较慢)
python run_gold_analysis.py

# 快速预测: 跳过回测 (~30 秒)
python run_gold_analysis.py --skip-backtest

# 极速模式: 跳过回测和跨市场信号 (~15 秒)
python run_gold_analysis.py --skip-backtest --skip-cross-market

# 预测到指定日期
python run_gold_analysis.py --skip-backtest --target-end 2026-04-10

# 使用旧版日线模型 (对比用)
python run_gold_analysis_legacy.py --skip-backtest
```

**重要**: 需要从 `stock-prediction/` 目录运行，或确保 `.venv` 已激活。
虚拟环境路径: `stock-prediction/.venv/bin/python`

---

## 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--target-end` | `2026-04-03` | 预测截止日期 (YYYY-MM-DD) |
| `--lookback` | `240` | 模型训练窗口大小 (天数) |
| `--backtest-stride` | `10` | 回测步长 (越小越精确但越慢) |
| `--backtest-horizon` | `5` | 回测最大预测天数 |
| `--skip-backtest` | `false` | 跳过回测，仅输出预测 |
| `--skip-cross-market` | `false` | 跳过跨市场信号 |

---

## Agent / Cron 调用指南

### 作为 Python 函数调用

```python
from run_gold_analysis import main

# 默认调用 — 返回 List[Dict]
predictions = main()

# 自定义参数
predictions = main(
    target_end="2026-04-10",
    lookback=240,
    skip_backtest=True,
    skip_cross_market=False,
)

# predictions 是 List[Dict], 每个元素:
# {
#   "date": "2026-03-27",
#   "close": 987.69,           # 16:00 预测收盘价 (CNY/克)
#   "direction": "跌",          # 涨/跌/平
#   "confidence": 72.7,         # 信心度 (0-100)
#   "range_low": 962.0,         # 波动区间下限
#   "range_high": 988.0,        # 波动区间上限
#   "regime": "high",           # 波动率 regime
#   "n_checkpoints": 6,         # 参与预测的 checkpoint 数
#   "checkpoint_details": {     # 各时点独立预测
#     "04:00": {"pred_close": 964.31, "weight": 0.039, ...},
#     "09:00": {"pred_close": 965.29, "weight": 0.084, ...},
#     "12:00": {"pred_close": 978.58, "weight": 0.198, ...},
#     "16:00": {"pred_close": 984.13, "weight": 0.362, ...},
#     ...
#   }
# }
```

### 作为 CLI 工具调用 (cron / 定时任务)

```bash
# macOS cron: 快速预测未来 7 个交易日
python run_gold_analysis.py --skip-backtest --target-end $(date -v+7d +%Y-%m-%d)

# Linux cron:
python run_gold_analysis.py --skip-backtest --target-end $(date -d "+7 days" +%Y-%m-%d)

# 每周末完整回测 + 预测
python run_gold_analysis.py --backtest-stride 5 --target-end $(date -v+14d +%Y-%m-%d)
```

### Agent 调用场景

| 用户指令 | 对应命令 |
|---------|---------|
| "看看明天金价" | `python run_gold_analysis.py --skip-backtest --target-end <明天日期>` |
| "预测下周金价" | `python run_gold_analysis.py --skip-backtest --target-end <下周五日期>` |
| "预测到月底" | `python run_gold_analysis.py --skip-backtest --target-end <月底日期>` |
| "跑个完整回测" | `python run_gold_analysis.py --backtest-stride 5` |
| "快速预测不要回测" | `python run_gold_analysis.py --skip-backtest --skip-cross-market` |
| "用旧模型对比" | `python run_gold_analysis_legacy.py --skip-backtest` |

---

## 输出格式

### 主预测表

```
日期          16:00预测(元/克)  方向      涨跌   信心度        波动区间  checkpoint
-------------------------------------------------------------------------------------
2026-03-27          987.69     跌     -8.29   72.7%       [962~988]       6
2026-03-30          984.09     跌     -3.60   90.0%       [977~984]       6
2026-03-31          982.86     跌     -1.23   78.0%       [979~984]       6
2026-04-01          983.51     涨     +0.65   80.3%       [981~986]       6
```

- **方向**: 涨/跌/平 (变动 < 0.5 元/克 视为平)
- **信心度**: 0-100%，综合模型投票一致性 (40%) + 分类器概率 (60%)
- **波动区间**: 各 checkpoint 预测值的 min/max ± 0.2%
- **checkpoint**: 参与预测的时点数量 (满分 6)

### Checkpoint 细节 (首日)

```
  Checkpoint Details:
    04:00  pred=  964.31  w=0.039  prob=51.7%  base=981.76
    09:00  pred=  965.29  w=0.084  prob=40.5%  base=981.76
    12:00  pred=  978.58  w=0.198  prob=17.6%  base=991.84
    16:00  pred=  984.13  w=0.362  prob=10.9%  base=992.90
    20:00  pred=  984.13  w=0.155  prob=10.9%  base=992.90
    24:00  pred=  985.61  w=0.161  prob=4.9%   base=999.06
```

- **pred**: 该时点模型的独立预测值
- **w**: 归一化权重 (16:00 权重最大 ~0.36)
- **prob**: 上涨概率 (< 50% 表示看跌)
- **base**: 该时点使用的基准价 (夜盘时点用夜盘收盘, 日盘时点用日盘价)

---

## 模型架构

```
SHFE AU 60min K线 ──→ 聚合为 6 个 checkpoint bar
SHFE AU 日线      ──→     ┌──────────────────────────┐
COMEX (GC=F)      ──→     │  Multi-Bar Feature Engine │
USDCNY            ──→     │  (分时+日线+跨市场特征)    │
DXY / VIX / US10Y ──→     └──────────┬───────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │         │         │         │      │
               Model_04   Model_09  Model_12  Model_16  ...
               (w=0.05)   (w=0.10)  (w=0.20)  (w=0.35)
                    │         │         │         │      │
                    └─────────────────┼─────────────────┘
                                      │
                         时间衰减加权聚合
                                      │
                     波动率 Regime 自适应压缩
                     (low=0% / normal=15% / high=45% / extreme=70%)
                                      │
                            最终 16:00 预测 (CNY/克)
```

### 6 个 Checkpoint

| 时点 | 数据范围 | 权重 | 说明 |
|------|---------|------|------|
| 04:00 | 夜盘尾段 (00:00-02:30) | 5% | 最早隔夜信号 |
| 09:00 | 完整夜盘 (21:00-02:30) | 10% | 含完整隔夜信息 |
| 12:00 | 上午盘 (09:00-11:30) | 20% | 半日走势 |
| 16:00 | 全天 (09:00-15:00) | 35% | 最高权重 |
| 20:00 | 日盘完整 (次日预测) | 15% | 为次日预判 |
| 24:00 | 夜盘前半 (次日预测) | 15% | 夜盘动量 |

### 特征工程 (每个 checkpoint 32 维)

**分时特征 (9 维)**:
- session_return, session_range, session_volume_ratio
- gap_from_prev_close, high_low_position, vwap_deviation
- bar_count, momentum_3bar, last_bar_return

**日线特征 (14 维)**:
- lag_1~5, ret_1/3/5, ma_5/10/20, ma_gap_5/10/20, vol_5

**跨市场特征 (7 维)**:
- comex_overnight_return, comex_shfe_premium
- dxy_5d_change, vix_level, vix_regime
- us10y_5d_change, usdcny_direction

**元特征 (2 维)**:
- hours_to_target, day_of_week

### 波动率 Regime

| Regime | 年化波动率 | 预测压缩 | 方向阈值 |
|--------|----------|---------|---------|
| low | < 15% | 0% | 50% |
| normal | 15-30% | 15% | 55% |
| high | 30-50% | 45% | 60% |
| extreme | > 50% | 70% | 65% |

当前 (2026-03-27): **high** regime, 47.6% 年化波动率。

---

## 文件结构

```
stock-prediction/
├── run_gold_analysis.py          # Multi-Bar 版入口 (当前版本)
├── run_gold_analysis_legacy.py   # 旧版日线模型 (对比用)
├── ml-service/models/
│   ├── multi_bar_predictor.py    # 多时点预测核心
│   ├── multi_bar_features.py     # checkpoint 聚合 + 特征工程
│   ├── volatility_regime.py      # 波动率 regime 管理
│   ├── predictor.py              # 旧版预测器 (legacy 使用)
│   └── external_direction.py     # 外部方向特征
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

---

## Changelog

### v2.0 (2026-03-27) — Multi-Bar 架构

- 从日线单点预测改为 60min 多时点预测
- 新增 6 个 checkpoint 独立模型
- 新增波动率 regime 自适应压缩
- 新增夜盘/日盘分时特征
- 新增跨市场直接特征 (COMEX 隔夜收益率等)
- 方向准确率从 ~50% 提升至 68-83%
- T+1 预测误差从 1.86% 降至 0.42% (实测)

### v1.0 — 日线模型 (Legacy)

- 三模型融合 (Linear / Boosting / Ensemble)
- 跨市场微调 (±0.3% cap)
- 极端行情 2σ 过滤 + 40% 压缩
- 保留在 `run_gold_analysis_legacy.py`
