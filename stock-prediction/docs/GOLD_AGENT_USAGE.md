# 黄金预测 Agent 调用手册

本文档是 `stock-prediction` 中黄金预测流程的 agent 调用契约，目标是让其它 agent 可以直接发起预测、读取结果。

## 当前版本: Multi-Bar v2 (2026-03-27)

模型已从日线单点预测升级为 **Multi-Bar 多时点预测架构**:

- 基于 SHFE AU 60min K 线的 6 个 checkpoint (04:00/09:00/12:00/16:00/20:00/24:00)
- 每个 checkpoint 独立训练 GBM 模型，目标统一为当日 16:00 收盘价
- 时间衰减加权聚合 + 波动率 regime 自适应压缩
- 实测 T+1 误差 0.42% (旧版 1.86%)，方向准确率 68-83% (旧版 ~50%)

### 关键改进

| 维度 | 旧版 (v1 日线) | 新版 (v2 Multi-Bar) |
|------|--------------|-------------------|
| 数据源 | 日线 close | 60min K线 (含夜盘) |
| 模型 | Linear/Boosting/Ensemble | 6x GBM per checkpoint |
| 方向准确率 | ~50% | 68-83% |
| 波动率处理 | 固定 2σ 压缩 40% | 4 档 regime 自适应 |
| 夜盘感知 | 无 | 04:00/09:00 checkpoint |
| 跨市场 | 微调 ±0.3% | 直接特征输入 |

## 推荐调用方式

### 方式 1: CLI 直接调用 (推荐)

```bash
cd /Users/rootliu/code/stock-prediction

# 快速预测 (推荐, ~30 秒)
.venv/bin/python run_gold_analysis.py --skip-backtest --target-end <截止日期>

# 含回测 (完整模式, 较慢)
.venv/bin/python run_gold_analysis.py --target-end <截止日期>

# 极速模式 (跳过跨市场)
.venv/bin/python run_gold_analysis.py --skip-backtest --skip-cross-market
```

### 方式 2: Python 函数调用

```python
import sys
sys.path.insert(0, "/Users/rootliu/code/stock-prediction")
from run_gold_analysis import main

predictions = main(
    target_end="2026-04-10",
    lookback=240,
    skip_backtest=True,
    skip_cross_market=False,
)

# predictions: List[Dict], 每个元素包含:
# {
#   "date": "2026-03-27",
#   "close": 987.69,            # 16:00 预测收盘价 (CNY/克)
#   "direction": "跌",           # 涨/跌/平
#   "confidence": 72.7,          # 信心度 (0-100)
#   "range_low": 962.0,          # 波动区间下限
#   "range_high": 988.0,         # 波动区间上限
#   "regime": "high",            # 波动率档位
#   "n_checkpoints": 6,          # 参与预测的时点数
#   "checkpoint_details": {...},  # 各时点独立预测 (可追溯)
# }
```

### 方式 3: Bot/Report 模式 (OpenClaw wrapper)

```bash
/Users/rootliu/code/stock-prediction/scripts/run_openclaw_report.sh /tmp/agent-gold-report
```

仍使用旧版 ensemble 模型生成完整报告包。下游 agent 读取顺序:
1. 等待 `manifest.json`
2. 读取 `report.md`
3. 读取 `gold_prediction.json` / `gold_forecast.csv`

### 方式 4: HTTP API

```bash
cd /Users/rootliu/code/stock-prediction/ml-service && python main.py

# 预测 (仍使用旧版 predictor, 可回退)
curl -sS -X POST http://127.0.0.1:8000/api/v1/gold/predict/SHFE_AU_MAIN \
  -H 'Content-Type: application/json' \
  -d '{"horizon": 5, "lookback": 120, "model_type": "ensemble"}'

# 辅助数据
curl -sS 'http://127.0.0.1:8000/api/v1/gold/quote/SHFE_AU_MAIN'
curl -sS 'http://127.0.0.1:8000/api/v1/gold/kline/SHFE_AU_MAIN?period=60min&session=ALL'
```

## 旧版模型 (对比/回退)

旧版日线模型保留在 `run_gold_analysis_legacy.py`:

```bash
.venv/bin/python run_gold_analysis_legacy.py --skip-backtest --source shfe
```

支持 `--source shfe|comex`，模型类型: linear / boosting / ensemble。

## Agent 调用场景映射

| 用户指令 | 命令 |
|---------|------|
| "看看明天金价" | `.venv/bin/python run_gold_analysis.py --skip-backtest --target-end <明天>` |
| "预测下周金价" | `.venv/bin/python run_gold_analysis.py --skip-backtest --target-end <下周五>` |
| "预测到月底" | `.venv/bin/python run_gold_analysis.py --skip-backtest --target-end <月底>` |
| "跑个回测" | `.venv/bin/python run_gold_analysis.py --backtest-stride 5` |
| "用旧模型对比" | `.venv/bin/python run_gold_analysis_legacy.py --skip-backtest` |
| "极速预测" | `.venv/bin/python run_gold_analysis.py --skip-backtest --skip-cross-market` |

## 输出字段说明

### Multi-Bar 模型输出 (run_gold_analysis.py)

关键字段:
- `close`: 16:00 预测收盘价 (CNY/克)
- `direction`: 涨/跌/平
- `confidence`: 信心度 (0-100)
- `range_low` / `range_high`: 波动区间
- `regime`: low/normal/high/extreme
- `checkpoint_details`: 6 个时点的独立预测

### 波动率 Regime 说明

| Regime | 年化波动率 | 预测压缩 | Agent 建议 |
|--------|----------|---------|-----------|
| low | < 15% | 0% | 正常参考预测值 |
| normal | 15-30% | 15% | 正常参考 |
| high | 30-50% | 45% | 降低仓位，扩大止损 |
| extreme | > 50% | 70% | 仅参考方向，不参考幅度 |

## 对其它 Agent 的建议

1. **优先使用 Multi-Bar CLI** (run_gold_analysis.py)，准确率最高
2. **关注 regime 字段**: high/extreme 时预测幅度不可靠，仅参考方向
3. **关注 confidence**: < 50% 时预测方向也不可靠
4. **checkpoint_details 可追溯**: 如果需要解释预测依据，展示各时点预测
5. **旧版 (legacy) 仅用于对比**，不作为生产默认

## 文件结构

```
stock-prediction/
├── run_gold_analysis.py              # Multi-Bar v2 入口 (推荐)
├── run_gold_analysis_legacy.py       # 旧版日线模型
├── GOLD_FORECAST_GUIDE.md            # 详细模型文档
├── ml-service/models/
│   ├── multi_bar_predictor.py        # 多时点预测核心
│   ├── multi_bar_features.py         # checkpoint 聚合 + 特征
│   ├── volatility_regime.py          # 波动率 regime
│   ├── predictor.py                  # 旧版预测器
│   └── external_direction.py         # 外部方向特征
├── scripts/
│   └── run_openclaw_report.sh        # OpenClaw wrapper (旧版)
└── docs/
    ├── GOLD_AGENT_USAGE.md           # 本文件
    └── OPENCLAW_INTEGRATION.md       # OpenClaw 集成文档
```
