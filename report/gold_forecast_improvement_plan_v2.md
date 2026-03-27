# Gold Forecast Improvement Plan v2 — Multi-Bar Intraday Prediction

> 基于 2026-03-27 回测分析，结合用户要求：用分时多 bar 数据代替纯日线，通过多时点预测加权聚合得到更准确的 16:00 收盘价。

---

## 核心思路变化

**旧方案**: 日线 close → 特征 → 预测下一日 close (单点输入、单点输出)

**新方案**: 多时段 bar (夜盘+日盘) → 丰富特征 → 多时点预测 (09:00/12:00/16:00/20:00/24:00/04:00) → 加权聚合 → 输出 16:00 代表价

```
数据流:

SHFE 60min K线 ──→ 聚合为 6 个时点 bar
COMEX 日线     ──→     ┌──────────────────────────┐
USDCNY         ──→     │  Multi-Bar Feature Engine │
DXY/VIX/US10Y  ──→     └──────────┬───────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
               pred_09:00    pred_12:00    pred_16:00  ...
                    │              │              │
                    └──────────────┼──────────────┘
                                   │
                          时间衰减加权聚合
                                   │
                           最终 16:00 预测
```

---

## Phase 1: Multi-Bar 数据基础 (Day 1-2)

### 1.1 定义 6 个预测时点

| 时点 | 含义 | 数据来源 | 说明 |
|------|------|---------|------|
| 04:00 | 凌晨 (COMEX 收盘后) | COMEX close + SHFE 夜盘尾段 | 最早的隔夜信号 |
| 09:00 | 日盘开盘前 | SHFE 夜盘完整数据 + COMEX 收盘 | 含完整隔夜信息 |
| 12:00 | 午盘 | SHFE 上午段 (09:00-11:30) | 含半日走势 |
| 16:00 | 日盘收盘 (目标) | SHFE 全天数据 | 最终输出 |
| 20:00 | 夜盘开盘前 | SHFE 日盘完整 + 欧盘开盘 | 为次日做预判 |
| 24:00 | 夜盘中段 | SHFE 夜盘前半 + COMEX 盘中 | 夜盘动量 |

### 1.2 数据获取函数

```python
def fetch_multi_bar_snapshot(target_date: str) -> Dict[str, pd.DataFrame]:
    """
    获取 target_date 的多时段 bar 数据。

    Returns:
        {
            "shfe_60min": DataFrame,  # SHFE AU 60min K线 (含 session 标记)
            "shfe_daily": DataFrame,  # SHFE AU 日线 (历史基准)
            "comex_daily": DataFrame, # COMEX 日线
            "usdcny": DataFrame,      # 汇率
            "cross_market": DataFrame, # DXY/VIX/US10Y
        }
    """
```

已有 `GoldMarketCollector._get_shfe_intraday("AU0", "60min")` 可直接获取 60min 数据，带 session (DAY/NIGHT) 标记。

### 1.3 Bar 聚合逻辑

```python
def aggregate_to_checkpoint_bars(shfe_60min: pd.DataFrame, date: str) -> Dict[str, Dict]:
    """
    将 60min K线聚合为 6 个 checkpoint bar。

    每个 bar 包含:
    - open, high, low, close, volume, vwap
    - session_return: 该时段内收益率
    - cumulative_return: 从前日16:00到当前的累计收益率
    - bar_volatility: 该时段内的波动率
    - volume_ratio: 该时段成交量 / 日均成交量
    """
    checkpoints = {
        "04:00": ("night", "00:00-02:30"),   # 夜盘尾段
        "09:00": ("pre_day", "21:00-02:30"),  # 完整夜盘
        "12:00": ("morning", "09:00-11:30"),  # 上午盘
        "16:00": ("full_day", "09:00-15:00"), # 全天
        "20:00": ("post_day", "09:00-15:00"), # 日盘完整 (同 16:00, 但加入欧盘)
        "24:00": ("night_first", "21:00-23:59"), # 夜盘前半
    }
```

---

## Phase 2: Multi-Bar Feature Engine (Day 2-3)

### 2.1 每个 Checkpoint 的特征集

**A. 价格动态特征 (来自 SHFE 60min)**

| Feature | 说明 |
|---------|------|
| `night_return` | 夜盘收益率 (21:00 open → 02:30 close) / prev_16:00 |
| `night_range` | 夜盘振幅 (high-low) / prev_16:00 |
| `night_volume_ratio` | 夜盘量 / 5日均夜盘量 |
| `morning_return` | 上午收益率 (09:00 open → 11:30 close) / night_close |
| `morning_gap` | 开盘跳空 (09:00 open - night_close) / night_close |
| `intraday_momentum` | 最近 3 个 60min bar 的方向一致性 |
| `vwap_deviation` | 当前价 vs VWAP 偏离度 |
| `session_volatility` | 当前 session 的已实现波动率 |
| `high_low_position` | (close - low) / (high - low) — 收在区间什么位置 |

**B. 跨市场特征 (来自 yfinance)**

| Feature | 说明 |
|---------|------|
| `comex_overnight_return` | COMEX 前日收益率 (对 09:00 bar 最有效) |
| `comex_shfe_premium` | SHFE 溢价率 = (shfe - comex_cny) / comex_cny |
| `dxy_5d_change` | 美元指数 5 日变化率 |
| `vix_level` | VIX 绝对水平 (分区: <15/15-25/25-35/>35) |
| `us10y_5d_change` | 10Y 国债收益率 5 日变化 |
| `usdcny_direction` | 汇率方向 (升值利空金, 贬值利多金) |

**C. 历史统计特征 (来自日线)**

保留原有: `lag_1~5, ret_1/3/5, ma_5/10/20, ma_gap_*, vol_5`

**D. 时点特有特征**

| Feature | 说明 |
|---------|------|
| `hours_to_target` | 距 16:00 还有几小时 (时间衰减权重的基础) |
| `bars_observed` | 当天已观察到多少个 60min bar |
| `day_of_week` | 周几 (0=Mon, 4=Fri) |

### 2.2 Feature Builder

```python
class MultiBarFeatureBuilder:
    """
    为每个 checkpoint 构建特征向量。

    输入: checkpoint bars + 日线历史 + 跨市场数据
    输出: 每个时点一个 feature vector
    """

    def build_features(
        self,
        checkpoint: str,        # "09:00", "12:00", etc.
        bars: Dict,             # checkpoint bar data
        daily_history: pd.DataFrame,
        cross_market: pd.DataFrame,
    ) -> pd.Series:
        ...
```

---

## Phase 3: Multi-Point Predictor (Day 3-4)

### 3.1 模型架构

每个 checkpoint 时点训练一个独立的预测器，目标统一为 **当日 16:00 close**:

```
Checkpoint 04:00 → Model_0400 → pred_close_16:00
Checkpoint 09:00 → Model_0900 → pred_close_16:00
Checkpoint 12:00 → Model_1200 → pred_close_16:00
Checkpoint 16:00 → Model_1600 → pred_close_16:00  (次日)
Checkpoint 20:00 → Model_2000 → pred_close_16:00  (次日)
Checkpoint 24:00 → Model_2400 → pred_close_16:00  (次日)
```

关键点: **所有模型的 target 都是同一个 16:00 close**，但输入的信息量不同（越接近 16:00 信息越多）。

### 3.2 模型选择

| Model | Type | Purpose |
|-------|------|---------|
| Regressor | GradientBoostingRegressor | 预测 close 值 |
| Classifier | GradientBoostingClassifier | 预测涨跌方向 |

不再使用 LinearRegression — 回测已证明 boosting 在 MAE 上显著优于 linear (3.53 vs 5.81)。linear 的方向准确率优势 (50.0 vs 47.6) 在统计上不显著。

### 3.3 训练数据构建

```python
def build_training_data(
    shfe_60min: pd.DataFrame,
    shfe_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    lookback_days: int = 240,
) -> Dict[str, Tuple[pd.DataFrame, pd.Series]]:
    """
    Returns: {
        "09:00": (X_features, y_16:00_close),
        "12:00": (X_features, y_16:00_close),
        ...
    }
    """
    # 对每一天:
    #   1. 取当天的 60min bars, 聚合到各 checkpoint
    #   2. 构建特征
    #   3. target = 当天 16:00 close (对于 20:00/24:00/04:00, target = 次日 16:00)
```

---

## Phase 4: Temporal Weighted Aggregation (Day 4)

### 4.1 加权策略

离 16:00 越近的预测，权重越大:

```python
CHECKPOINT_WEIGHTS = {
    "04:00": 0.05,   # 12h before, minimal weight
    "09:00": 0.10,   # 7h before, night info incorporated
    "12:00": 0.20,   # 4h before, morning session known
    "16:00": 0.35,   # same-day model (from prev day 16:00 features → today's 16:00)
    "20:00": 0.15,   # next-day prediction (from today's full day)
    "24:00": 0.15,   # next-day with early night session
}
```

### 4.2 动态权重调整

```python
def compute_dynamic_weights(
    predictions: Dict[str, float],
    confidences: Dict[str, float],
    base_weights: Dict[str, float],
) -> Dict[str, float]:
    """
    基础权重 × 模型信心度 × 方向一致性奖励

    - 如果多个时点方向一致, 给一致方向的预测更高权重
    - 如果某个时点信心度很低 (<40%), 降低其权重
    - 最终归一化
    """
```

### 4.3 聚合输出

```python
def aggregate_predictions(
    checkpoint_predictions: Dict[str, Dict],
) -> Dict[str, Any]:
    """
    Returns:
        {
            "close": 加权平均 close,
            "direction": 多数投票方向,
            "confidence": 加权信心度,
            "range_low": min(各 checkpoint pred) * 0.998,
            "range_high": max(各 checkpoint pred) * 1.002,
            "checkpoint_details": {  # 可追溯
                "09:00": {"pred": 998.5, "weight": 0.15, "confidence": 62.3},
                ...
            }
        }
    """
```

---

## Phase 5: Volatility Regime Adaptation (Day 4-5)

### 5.1 波动率自适应

```python
def get_volatility_regime(daily_closes: pd.Series, window: int = 20) -> str:
    """
    Returns: "low" | "normal" | "high" | "extreme"

    Based on annualized realized volatility:
    - low:     < 15%
    - normal:  15% - 30%
    - high:    30% - 50%
    - extreme: > 50% (当前状态 ~86%)
    """

REGIME_DAMPENING = {
    "low": 1.0,       # 低波时不压缩
    "normal": 0.85,    # 轻微压缩
    "high": 0.55,      # 大幅压缩
    "extreme": 0.30,   # 极端压缩 (当前应适用此档)
}
```

### 5.2 应用位置

在最终聚合后:
```python
raw_change = aggregated_close - prev_close_16
dampened_change = raw_change * REGIME_DAMPENING[regime]
final_close = prev_close_16 + dampened_change
```

以昨天为例:
- 原始预测变动: +14.33
- 极端 regime 压缩: +14.33 × 0.30 = **+4.30**
- 预测值: 995.98 + 4.30 = **1000.28** (比原来的 1010.31 好很多, 实际 991.88)

---

## Phase 6: Revised Backtest Framework (Day 5-6)

### 6.1 多 bar 回测

```python
def multi_bar_backtest(
    shfe_60min: pd.DataFrame,
    shfe_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    lookback: int = 240,
    stride: int = 5,
) -> pd.DataFrame:
    """
    Walk-forward 回测:
    1. 对每个 origin, 模拟各 checkpoint 的预测
    2. 聚合后 vs 实际 16:00 close
    3. 对比: 多 bar 聚合 vs 单日线预测 (baseline)
    """
```

### 6.2 期望指标改善

| Metric | 当前 (日线) | 目标 (多 bar) | 改善幅度 |
|--------|-----------|-------------|---------|
| T+1 MAE | 3.53 | < 2.5 | -30% |
| T+1 MAPE | 0.92% | < 0.65% | -30% |
| 方向准确率 | 47.6% | > 55% | +15% |
| 极端行情 MAE | ~18+ | < 8 | -55% |

---

## Phase 7: Output Format Update (Day 6)

### 7.1 新输出格式

```
========================================================================
  黄金价格预测 — SHFE AU (CNY/克) — Multi-Bar Model
========================================================================

日期        16:00预测  方向  涨跌    信心度  波动区间         数据时点
--------------------------------------------------------------------------
2026-03-27   1000.28   涨  +4.30   58.2%  [994~1006]    09:00 (含夜盘)
2026-03-28    998.50   跌  -1.78   52.1%  [993~1004]    16:00 (全天)
2026-03-31   1002.30   涨  +3.80   45.6%  [995~1009]    16:00 (全天)

  Checkpoint Details (2026-03-27):
    04:00  pred=997.2  w=0.05  conf=42%  (COMEX 隔夜跌, 夜盘弱)
    09:00  pred=999.8  w=0.12  conf=55%  (夜盘收 981.76, gap down)
    12:00  pred=1001.5 w=0.22  conf=61%  (上午反弹至 994)
    16:00  pred=1002.1 w=0.35  conf=58%  (日线模型)
```

---

## Implementation File Structure

```
ml-service/models/
├── predictor.py              # 现有 (保留, 作为 baseline)
├── multi_bar_predictor.py    # 新: 多 bar 预测核心
├── multi_bar_features.py     # 新: 多 bar 特征工程
├── volatility_regime.py      # 新: 波动率 regime 管理
└── external_direction.py     # 现有

run_gold_analysis.py          # 改造: 调用 multi_bar_predictor
run_gold_analysis_legacy.py   # 备份: 原日线版本
```

---

## Implementation Order

| Step | Task | Depends On | Effort |
|------|------|-----------|--------|
| 1 | `volatility_regime.py` — 波动率 regime + dampening | None | 1h |
| 2 | `multi_bar_features.py` — checkpoint 聚合 + 特征 | None | 4h |
| 3 | `multi_bar_predictor.py` — 多时点模型训练 + 加权聚合 | 1, 2 | 6h |
| 4 | 改造 `run_gold_analysis.py` — 接入新预测器 | 3 | 2h |
| 5 | 多 bar 回测 + 与旧模型对比 | 4 | 3h |
| 6 | 输出格式 + checkpoint 细节展示 | 4 | 1h |
| **Total** | | | **~17h** |

---

## Quick Win (可先做, 1-2h)

在不重构模型的情况下，先将 **P5 波动率压缩** 和 **P1 夜盘 gap 修正** 加入现有 `run_gold_analysis.py`:

```python
# 在 sequential_forecast() 的 _weighted_combine 之后:

# 1. 获取夜盘最新价作为 effective base
night_close = fetch_latest_night_close()  # 从 60min K线
if night_close is not None:
    effective_base = night_close
else:
    effective_base = prev_close

# 2. 波动率 regime 压缩
regime = get_volatility_regime(history_close)
dampening = REGIME_DAMPENING[regime]
final = effective_base + (combined - effective_base) * dampening
```

这个快速修正不改变模型架构，但能立即减少 overnight gap 误差和高波动率过度预测。
