# 黄金预测 Agent 调用手册

本文档是 `stock-prediction` 中黄金预测流程的 agent 调用契约，目标是让其它 agent 可以直接发起预测、生成可展示的汇报版 Markdown，并读取表格、图片与解释。

## 当前推荐路径

如果是“给用户看结果”的定时任务，默认走：

- `run_gold_analysis.py`
- `--forecast-mode direct`
- `--skip-backtest`
- `--report-dir <输出目录>`

原因：

- `direct` 更适合 `T+1 ~ T+5` 的多日外推
- 程序会自动输出 `bull / base / bear` 三情景
- 会同时生成 Markdown、CSV、JSON、PNG
- Markdown 已包含“汇报版”、解释、表格和图片链接

如果是研究/验证任务，再加：

- `--backtest-stride <N>`
- 不使用 `--skip-backtest`

## 模型分工

| 路径 | 适合场景 | 默认建议 |
|------|---------|---------|
| `multibar` | 同日 16:00 nowcast、看夜盘对白盘的影响 | 保留，用于研究或同日预测 |
| `direct` | 多日外推、定时汇报、agent 自动化 | 推荐 |
| `legacy` | 旧版对比、回退 | 仅对比/回退 |

## 推荐调用方式

### 方式 1: CLI 直接调用 (推荐)

```bash
cd /Users/rootliu/code/stock-prediction

# 快速预测 + 生成汇报版 Markdown/PNG (推荐)
.venv/bin/python run_gold_analysis.py \
  --forecast-mode direct \
  --skip-backtest \
  --target-end <截止日期> \
  --report-dir /Users/rootliu/code/report

# 含回测与事件区间回测 (完整模式, 较慢)
.venv/bin/python run_gold_analysis.py \
  --forecast-mode direct \
  --target-end <截止日期> \
  --backtest-stride 60 \
  --report-dir /Users/rootliu/code/report

# 关闭事件层，仅输出基础预测
.venv/bin/python run_gold_analysis.py \
  --forecast-mode direct \
  --skip-backtest \
  --target-end <截止日期> \
  --disable-event-scenarios \
  --report-dir /Users/rootliu/code/report
```

### 定时任务：生成、校验、推送

工作日上海时间 09:00 和 20:00 的现行入口如下。不传截止日期表示最近已完成沪金日线之后的第三个交易日，早盘不会使用当天未收盘价格。

```cron
0 9,20 * * 1-5 /Users/rootliu/code/stock-prediction/scripts/run_gold_direct_report.sh /tmp/gold-direct-agent >> /tmp/gold-direct-agent.log 2>&1
```

1. 等待本次进程结束，记录其打印的 `runs/<run_id>`；若被中断或未得到本次编号，不得发送旧报告。
2. 读取该运行目录内的 `manifest.json`；核对 `run_id`。根目录同名文件仅指向最近一次运行，看到 `running` 不推送。
3. 退出码 0 且 `status=ok` 时，按 `files` 相对**输出根目录**取本次 Markdown、PNG、CSV、JSON，逐项核对 `sha256`。发送“汇报版”和图片；正文点位、事件情景、实验价格区间与方向概率不可混用。
4. 退出码 2 且 `status=no_forecast` 时，只发本次 `files.report_md` 行情告警。不搜索旧文件，不复用上一期价格和图片。
5. 飞书 API 返回真实消息 ID 后才登记回执：`.venv/bin/python scripts/gold_publish.py <输出根目录> --ack <run_id> <飞书消息ID>`。生成成功不等于送达成功。

用于长期校准或投递审计时选用持久化输出目录；系统可能清空 `/tmp`。设置 `GOLD_SHADOW_INTERVAL=0` 可关闭实验区间，不改变点位或方向。当前显式交易日历覆盖 2026 年，未配置年份拒绝发布。

### 方式 2: Python 函数调用

仅供研究：直接调用函数不会产生带校验和的发布清单，不能代替 cron 入口。

```python
import sys
sys.path.insert(0, "/Users/rootliu/code/stock-prediction")
from run_gold_analysis import main

predictions = main(
    target_end="2026-04-10",
    lookback=240,
    skip_backtest=True,
    skip_cross_market=False,
    forecast_mode="direct",
    report_dir="/Users/rootliu/code/report",
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
#   "n_models": 1,               # direct 模型数量
#   "model_details": {...},      # 该 horizon 的训练摘要
#   "scenarios": {               # 若开启事件层，会补充三情景
#       "bear_close": ...,
#       "base_close": ...,
#       "bull_close": ...,
#       "bull_driver": "...",
#       "bear_driver": "...",
#   }
# }
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
| "看看明天金价" | `.venv/bin/python run_gold_analysis.py --forecast-mode direct --skip-backtest --target-end <明天> --report-dir /Users/rootliu/code/report` |
| "预测到 4/3" | `.venv/bin/python run_gold_analysis.py --forecast-mode direct --skip-backtest --target-end 2026-04-03 --report-dir /Users/rootliu/code/report` |
| "预测下周金价" | `.venv/bin/python run_gold_analysis.py --forecast-mode direct --skip-backtest --target-end <下周五> --report-dir /Users/rootliu/code/report` |
| "跑个回测" | `.venv/bin/python run_gold_analysis.py --forecast-mode direct --target-end <截止日期> --backtest-stride 60 --report-dir /Users/rootliu/code/report` |
| "用旧模型对比" | `.venv/bin/python run_gold_analysis_legacy.py --skip-backtest` |
| "极速预测" | `.venv/bin/python run_gold_analysis.py --forecast-mode direct --skip-backtest --skip-cross-market --target-end <截止日期>` |

## 输出字段说明

### `run_gold_analysis.py` 输出产物

正式 direct 发布将文件写入 `<输出根目录>/runs/<run_id>/`（回测附件仅在运行对应模块时生成）：

- `gold_direct_scenario_<latest_date>.md`
- `gold_direct_scenario_<latest_date>.png`
- `gold_direct_scenario_<latest_date>.csv`
- `gold_direct_scenario_<latest_date>.json`
- `gold_direct_scenario_<latest_date>_backtest.csv`
- `gold_direct_scenario_<latest_date>_event_backtest.csv`

根目录保留以下兼容入口。机器读取以本次清单的状态和文件路径为准：

- `report.md`
- `scenario.png`
- `scenario.csv`
- `scenario.json`
- `manifest.json`

### 汇报版 Markdown 结构

生成的 Markdown 已经包含：

1. `汇报版`
2. 三情景表格：`Bear / Base / Bull / 置信度 / 驱动解释`
3. 曲线图 PNG 引用
4. 调用说明
5. 完整预测表
6. Event Features / Event Calibration / Key Headlines
7. Base Backtest / Event Interval Backtest

其它 agent 应优先直接转发这个 Markdown，而不是自己重新拼接。

### Direct 模型输出字段

关键字段:
- `close`: 16:00 预测收盘价 (CNY/克)
- `direction`: 涨/跌/平
- `confidence`: 信心度 (0-100)
- `range_low` / `range_high`: 波动区间
- `regime`: low/normal/high/extreme
- `model_details`: 当前 horizon 的 direct 模型摘要
- `scenarios.bear_close / base_close / bull_close`: 三情景价格
- `scenarios.bull_driver / bear_driver`: 可解释路径

### 波动率 Regime 说明

| Regime | 年化波动率 | 预测压缩 | Agent 建议 |
|--------|----------|---------|-----------|
| low | < 15% | 0% | 正常参考预测值 |
| normal | 15-30% | 15% | 正常参考 |
| high | 30-50% | 45% | 降低仓位，扩大止损 |
| extreme | > 50% | 70% | 仅参考方向，不参考幅度 |

## 对其它 Agent 的建议

1. **默认用 `direct + report-dir`**，因为这是最适合自动汇报的产物链路
2. **优先展示 Markdown 和 PNG**，不要自己二次造表，避免口径漂移
3. **关注 regime 字段**：`high/extreme` 时幅度更适合看区间，不适合看单点
4. **关注 confidence**：`< 50%` 时方向信号偏弱，建议强调区间而不是方向
5. **展示 explanation**：优先使用 `bull_driver / bear_driver` 和 `Event Features`
6. **旧版 (legacy) 仅用于对比**，不作为生产默认

## 文件结构

```
stock-prediction/
├── run_gold_analysis.py              # direct / multibar 统一入口 (推荐)
├── run_gold_analysis_legacy.py       # 旧版日线模型
├── GOLD_FORECAST_GUIDE.md            # 详细模型文档
├── ml-service/models/
│   ├── multi_bar_predictor.py        # 多时点预测核心
│   ├── multi_bar_features.py         # checkpoint 聚合 + 特征
│   ├── multi_day_direct_predictor.py # 多日直推模型
│   ├── event_sentiment.py            # 事件/新闻/博客情景层
│   ├── volatility_regime.py          # 波动率 regime
│   ├── predictor.py                  # 旧版预测器
│   └── external_direction.py         # 外部方向特征
├── ml-service/data/
│   └── event_context.csv             # 本地事件日历模板
└── docs/
    ├── GOLD_AGENT_USAGE.md           # 本文件
    └── OPENCLAW_INTEGRATION.md       # OpenClaw 集成文档
```
