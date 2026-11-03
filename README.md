# 股票预测分析系统

基于 AI 的股票预测分析系统，支持 A 股和港股市场。

## 📁 项目结构

```
stock-prediction/
├── client/                 # 前端 React 项目
│   ├── src/
│   │   ├── components/    # 组件
│   │   │   ├── KLineChart.tsx    # K线图表
│   │   │   ├── StockList.tsx     # 股票列表
│   │   │   └── IndexBar.tsx      # 指数行情条
│   │   ├── services/      # API 服务
│   │   │   └── api.ts
│   │   ├── store/         # 状态管理
│   │   │   └── index.ts
│   │   ├── types/         # 类型定义
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── ml-service/            # Python ML 服务
│   ├── data_collector/    # 数据采集
│   │   ├── a_stock.py     # A股数据
│   │   └── hk_stock.py    # 港股数据
│   ├── utils/             # 工具函数
│   │   └── indicators.py  # 技术指标
│   ├── models/            # 预测模型
│   ├── backtest/          # 回测系统
│   ├── main.py
│   └── requirements.txt
│
├── server/                # Node.js 后端
│   └── ...
│
└── docs/
    └── REQUIREMENTS.md
```

## 🖥 服务器每日预测（上线入口）

> 这一节给跑 cron 的 server 看。生产入口是 `scripts/gold_daily.py`；旧的 `run.py --bot-output-dir` 仍然保留，两者请用**不同的输出目录**，避免同名文件互相覆盖。

### 一分钟部署

```bash
git clone git@github.com:rootliu/stock-prediction.git /srv/gold/app
cd /srv/gold/app
python3 -m venv .venv && .venv/bin/pip install -r ml-service/requirements.txt

# 1) 自检：19 项测试，全部应通过
.venv/bin/python -m pytest tests -q

# 2) 离线干跑：不联网、不推送，验证产物格式
.venv/bin/python scripts/gold_daily.py \
  --predictions-csv report/review_20260913/local_predictions.csv \
  --out /tmp/gold-dry --dry-run

# 3) 实跑：联网抓行情 + 跑模型
.venv/bin/python scripts/gold_daily.py --live --out /srv/gold/out
```

### cron

```cron
# 交易日收盘后 16:10；失败不静默——非 0 退出交给监控告警
10 16 * * 1-5 cd /srv/gold/app && .venv/bin/python scripts/gold_daily.py --live --out /srv/gold/out >> /srv/gold/logs/daily.log 2>&1
```

飞书推送：

```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxxx"
# 或显式传参：--feishu-webhook "$FEISHU_WEBHOOK_URL"
```

> 只从环境变量读 webhook，**不要在仓库里写任何 token / secret**。

### 可选：把日报也同步回仓库

`--publish-dir` 会把当天报告额外拷贝成 `report/daily/YYYY-MM-DD.md` 并追加一行索引，方便事后查阅、也让协作者不必登录 server 就能看到结果。

```cron
# 与上面同一时间段；需要 server 上有可推送的 deploy key
30 16 * * 1-5 cd /srv/gold/app && .venv/bin/python scripts/gold_daily.py --live --out /srv/gold/out --publish-dir report/daily && git add report/daily && git commit -m "chore: gold daily $(date +\%F)" && git push
```

### 退出码（决定了监控怎么配）

| 码 | 含义 | 建议动作 |
|---|---|---|
| 0 | 正常 | — |
| 2 | 数据问题（空预测、价格非法、无未来交易日） | 重试一次，仍失败再报警 |
| 3 | 质量闸门 | 查看 `report.md` 的闸门说明 |
| 4 | 未预期异常 | 报警，保留日志 |

### 产物与契约

输出到 `--out` 目录（原子写，中断不会留半成品）：

- `report.md` — 人读版：基准价、逐日预测、80% 区间、滚动 skill
- `gold_prediction.json` — 机器读版：`origin_date / origin_close / version / gate_note / rows[]`
- `gold_forecast.csv` — 逐日表：`baseline_close / model_close / raw_model_close / range_low / range_high`
- `forecasts.jsonl` — append-only 台账，每次运行追加一行，**不回写历史**

`rows[]` 每条含 `date, horizon, baseline_close, model_close, range_low, range_high`。新增字段只会追加，不改名、不删除。

### 数据降级与缓存

Yahoo 会在高频请求下限流（`YFRateLimitError`），新浪偶发 TLS 断连。每日任务因此带一层缓存：

- 抓取成功后写入 `.cache/gold/{shfe,comex,usdcny,cross}.csv`（已 gitignore）
- 抓取失败时回退到缓存，并把「数据截至哪天」写进 `report.md` 的 ⚠️ 行和 JSON 的 `data_warnings`
- **没有缓存则直接失败（退出码 2）**，不会拿残缺输入静默出一份预测

首次部署请先手动跑一次 `--live` 建立缓存，之后再交给 cron。

### 版本与闸门

- 上线版本：`v7`（模型收益 × 分段收缩 0.30/0.25/0.20/0.10）
- 自动降级：最近 30 条成熟样本的滚动 `skill < -0.05` 时，自动回退 `v0`（价格不变），并在 `report.md` 的"闸门"一行写明
  - 成熟样本来自 `forecasts.jsonl` 回填：每次运行会把台账里**目标日已到**的历史预测与真实收盘对账，因此闸门要跑几天后才开始生效
  - 对账用的是 `raw_model_close`（收缩前的原始模型价），避免版本变换被重复应用
- 手动指定：`--version v0|v1|v3|v4|v7`

重跑回测、更换 champion：

```bash
# 用仓库自带固定快照
.venv/bin/python scripts/bench_versions.py --from-snapshot

# 用 server 上最新一次模型输出
.venv/bin/python scripts/bench_versions.py --predictions /path/to/predictions.csv
```

输出在 `config/gold_versions/`（`leaderboard.md` 是给人看的结论，`calibration.json` 是每日任务用的区间校准）。

> 与 `scripts/run_gold_model_leaderboard.py` 的分工：那个做**模型/特征消融**（要重训，慢）；`bench_versions.py` 只做**后处理版本对比**（不重训，秒级）。日常选 champion 用后者。

### 当前基线（务必如实告知使用者）

在 2026-09-13 固定快照上，各版本相对"价格不变"的 skill：

| 版本 | T+1 | T+3 | T+5 | T+10 |
|---|---:|---:|---:|---:|
| v0 基线 | 0.000 | 0.000 | 0.000 | 0.000 |
| **v7 上线版** | −0.024 | −0.016 | −0.011 | −0.002 |
| v1 旧模型 | −0.166 | −0.105 | −0.054 | −0.041 |

**v7 没有优于"价格不变"，只是损失最小的信息型版本**（方向 95% 置信区间下限 30.1%，无方向优势）。报告里必须保留这条披露，不得宣传为"预测准确"。

### 回滚

```bash
# 换回基线
.venv/bin/python scripts/gold_daily.py --live --out /srv/gold/out --version v0
# 或整体回滚代码
cd /srv/gold/app && git checkout <上一个 tag>
```

---

## 🚀 快速启动

### 统一入口

```bash
cd stock-prediction
python run.py
```

默认行为：

- 不带参数：启动图形界面（后端 `8000` + 前端 `3000`）
- 带 `--bot-output-dir`：不启动图形界面，直接生成机器人可读取的巡检报告包

机器人巡检模式示例：

```bash
cd stock-prediction
python run.py --bot-output-dir /path/to/openclaw/stock-prediction
```

OpenClaw 旧巡检包也可以直接用：

```bash
scripts/run_openclaw_report.sh /path/to/openclaw/stock-prediction
```

或者通过环境变量：

```bash
export OPENCLAW_OUTPUT_DIR=/path/to/openclaw/stock-prediction
python run.py
```

输出目录会生成：

- `manifest.json`
- `report.md`
- `gold_quote.json`
- `gold_prediction.json`
- `gold_history.csv`
- `gold_forecast.csv`
- `gold_compare.csv`
- `gold_session.csv`
- `external_gold_survey.csv`
- `gold_curve_comparison.csv`
- `gold_external_main_curve.csv`
- `gold_prediction.png`
- `gold_compare.png`
- `gold_session.png`
- `gold_curve_comparison.png`
- `gold_summary_table.png`
- `gold_forecast_table.png`
- `gold_external_survey_table.png`
- `gold_curve_comparison_table.png`

机器人模式里的黄金报告现在包含 3 条曲线：

- 外部英文金融网站主曲线：基于英文金融网站 survey 的主线判断，作为主曲线
- 内部模型曲线：程序短期预测结果
- 融合曲线：以外部主曲线为主、内部模型为辅的折中结果

黄金主图默认使用：

- 过去 7 天真实走势
- 未来 5 天预测走势
- 每 4 小时一个时间点

外部方向因子支持本地 CSV 手动更新，默认路径：

- `ml-service/data/external_direction_signal.csv`

CSV 列格式：

- `published_at,source,direction_score,confidence,half_life_days`

说明：

- `direction_score` 范围 `[-1, 1]`，正值偏多，负值偏空
- `confidence` 范围 `[0, 1]`
- `half_life_days` 为观点衰减半衰期（天）

同时会输出逐日偏离表，并把内部模型相对外部主线的偏离标记为：

- `接近外部主线`
- `偏离较大(偏多/偏空)`
- `过于激进(偏多/偏空)`

### 前端

```bash
cd stock-prediction/client
npm install
npm run dev
```

### ML 服务

```bash
cd stock-prediction/ml-service
pip install -r requirements.txt
python main.py
```

### 4 小时预测与回测（黄金）

当前默认预测粒度为 `4h`。`15min/30min` 仍可用于研究，但不是主流程默认配置。

```bash
.venv/bin/python ml-service/backtest/gold_rolling_backtest.py \
  --source SHFE_AU_MAIN \
  --period 4h \
  --session ALL \
  --lookback 120 \
  --max-horizon 5 \
  --stride 2 \
  --start-date 2026-03-01 \
  --end-date 2026-03-23 \
  --output-dir /tmp/gold-backtest-4h
```

Bot 模式默认也会使用 `4h` 作为黄金巡检图表与预测粒度。

旧巡检包的黄金预测默认策略为 `ensemble`，保留两种回退方式：

- `boosting`
- `linear`

### Agent 调用索引

如果需要让其它 agent 直接调用黄金预测流程，优先看这两份文档：

- `docs/GOLD_AGENT_USAGE.md`：黄金预测 agent 调用手册，包含默认参数、回退方式、HTTP API 和输出契约
- `docs/OPENCLAW_INTEGRATION.md`：OpenClaw/cron 无界面巡检接入方式

推荐调用约定：

- cron / agent 默认入口使用 `scripts/run_gold_direct_report.sh`
- 默认预测链路使用 `run_gold_analysis.py --forecast-mode direct --skip-backtest`
- direct V3 guards 保持开启
- 旧巡检包默认粒度使用 `4h`
- 旧巡检包默认模型使用 `ensemble`
- 需要回退时显式指定 `boosting` 或 `linear`
- 机器人模式以下游读取 `manifest.json` 作为完成标记
- 现阶段不要把 `15min/30min` 作为 agent 默认入口
- 如果需要直接产出“汇报版 + 三情景 + 图片”的新黄金报告，优先使用 `scripts/run_gold_direct_report.sh`

最小调用示例：

```bash
scripts/run_gold_direct_report.sh /tmp/gold-direct-agent
```

新黄金情景报告的最小调用示例：

```bash
scripts/run_gold_direct_report.sh /tmp/gold-direct-agent 2026-04-03
```

需要显式指定模型时：

```bash
OPENCLAW_PREDICT_MODEL=ensemble scripts/run_openclaw_report.sh /tmp/agent-gold-report
OPENCLAW_PREDICT_MODEL=boosting scripts/run_openclaw_report.sh /tmp/agent-gold-report
OPENCLAW_PREDICT_MODEL=linear scripts/run_openclaw_report.sh /tmp/agent-gold-report
```

直接调用 API：

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/gold/predict/SHFE_AU_MAIN \
  -H 'Content-Type: application/json' \
  -d '{"horizon": 5, "lookback": 120, "model_type": "ensemble"}'
```

## 黄金续接回测（2026-09-12）

生产调用保持 `scripts/run_gold_direct_report.sh`，仍使用 V3 direct + guards；
本次没有替换预测模型或调整权重。

```bash
cd /path/to/stock-prediction
MPLCONFIGDIR=/tmp/mpl-stock .venv/bin/python scripts/run_gold_continuation_backtest.py \
  --cutoff 2026-09-04 --report-dir /tmp/gold-backtest --repo-report-dir /tmp/gold-backtest
MPLCONFIGDIR=/tmp/mpl-stock .venv/bin/python scripts/test_gold_continuation.py
```

`--cutoff` 为目标日期的排他下界，拉取最新数据后只评估已实现的目标。
脚本逐起点打印进度；同一起点跨周期复用特征，但不跨起点共享缓存。
返回预测按模型的实际 horizon 和目标日期匹配，避免缺失周期导致错位。
CSV 包含逐条预测、实际价格、误差、方向和信心评分。
信心评分不是校准后的正确概率；日线跨市场数据尚有可用时间对齐限制。
详见 [本轮回测及限制](report/gold_review_2026-09-12/review.md)。

## ✨ 功能特性

- 📊 K线图表（支持日/周/月K线切换）
- 📈 技术指标（MA、MACD、RSI、布林带等）
- 💰 A股和港股实时行情
- ⭐ 自选股管理
- 🔔 买卖信号提示
- 🤖 AI 预测模型
- 📉 回测系统
- 🌐 外部英文金融网站黄金共识曲线对比

## 🛠️ 技术栈

### 前端
- React 18 + TypeScript
- Vite + Ant Design
- ECharts（K线图）
- Zustand（状态管理）
- Axios（HTTP客户端）

### 后端
- Python + FastAPI
- TensorFlow/PyTorch（机器学习）
- Pandas/NumPy（数据处理）

## 📝 环境要求

- Node.js 18+
- Python 3.10+
- npm 或 yarn

## 📄 许可证

MIT License

## Direction Confidence v2 (2026-09-16)

固定生产入口不变：`scripts/run_gold_direct_report.sh <output-dir> [target-end]`。
价格、方向 guard 和价格区间保留原算法；仅重新定义 direct 输出的方向置信字段。

- `confidence`：最终价格方向对应的涨/跌/平概率估计，百分数，不再是强度分。
- `up_probability/down_probability/flat_probability`：0~1，合计为 1；相对预测基准价 +/-0.5 元视为平。
- `confidence_method=maturity_bin_dirichlet_v2`：训练集按标签成熟时间 purge；校准集按实际起止日期取非重叠样本，避免缺失交易日导致错位。校准与实时评分使用同一个重训前分类器，不得使用全量重训分类器的训练内分数或分支概率。
- `confidence_low/high`：所选方向频率的 90% Beta 后验区间，非价格区间；不涵盖市场分布变化。
- `calibration_count`：命中概率桶的非重叠标签数量；`calibration_total` 是全部校准样本数。
- `direction_signal=watch`：样本少于 10、价格方向与最高概率冲突、概率低于 60% 或区间下界不超过 50%。其它 agent 必须保留观望及原因，不得只转发一个百分数。
- `confidence_status=experimental_not_validated`：尚未通过独立长期校准验证，`supported` 也不是交易许可。
- `legacy_confidence_score`：原始强度分，仅供对照。模型详情中的 `up_probability` 仍是旧分支原始值；扁平 API 将其命名为 `branch_raw_up_probability`。

校准为三个固定桶（1/3、2/3 分界），固定 Dirichlet 先验 `[4.75, 0.5, 4.75]`（跌/平/涨），总强度 10。参数未按本次外层回测择优调参。长期稀疏样本会明显收缩，不能据此宣称更高准确率。

```bash
# 默认方向概率版
scripts/run_gold_direct_report.sh /tmp/gold-report
# 回退旧评分；不变更 cron、入口或价格模型
GOLD_DIRECTION_CONFIDENCE_MODE=legacy scripts/run_gold_direct_report.sh /tmp/gold-legacy
# 回测与概率评估
MPLCONFIGDIR=/tmp/mpl-stock .venv/bin/python scripts/run_gold_continuation_backtest.py \
  --cutoff 2026-08-28 --report-dir /tmp/gold-backtest --repo-report-dir /tmp/gold-backtest
.venv/bin/python scripts/evaluate_direction_confidence.py \
  /tmp/gold-backtest/gold_continuation_backtest_2026-08-28_to_2026-09-15.csv --output /tmp/gold-evaluation
.venv/bin/python scripts/test_direction_confidence.py
MPLCONFIGDIR=/tmp/mpl-stock .venv/bin/python scripts/test_gold_continuation.py
```

报告：`report/gold_confidence_2026-09-16/review_v2.md`。`review.md` 是合并远端修复前的历史实验，不能代表当前模型。v2 保留远端数据可用时间过滤、成熟标签 purge 与全量价格模型重训；无 available_at 的外部日线仍采用次日上海 08:00 假设，不是已核验的真实发布时间。

评估脚本另输出 `direction_threshold_audit.csv`：逐期限、上涨/下跌/横盘、50/60/70% 阈值的覆盖率与实际命中率，并提供 90% Wilson 区间。每个期限先按日期剔除重叠标签，跨期限仍有相关性；少于 30 条标记 insufficient_evidence，不得用少量连续同向行情证明可靠。

### 2026-11-03 每日任务可靠性修复

`scripts/gold_daily.py` 保留另一台机器新增的版本注册、缓存回退、账本和发布功能。
滚动 skill 现在仅使用 `origin_date < 当前起点` 且 `target_date <= 当前起点` 的成熟结果，
避免用未来实际价格决定历史版本回退。日线口径假设任务在起点日收盘后运行，不适用于盘中回放。
输入的日期、价格、整数期限、重复起点/期限及同一起点价格一致性均会校验；无效数据退出码为 2。
JSON 新增 `skill_version`、`skill_as_of`、`skill_sample_count`、`rolling_skill` 与
`direction_probability_status=not_estimated`。skill 属于回退前候选版本，不是回退后版本的成绩。
成熟样本数不是独立样本数；80% 价格区间也不是涨跌置信度。

旧的 `scripts/run_gold_direct_report.sh` 和 `run_gold_analysis.py` 路线未改动；没有修改 cron。
本次验证及局限见 `report/gold_daily_review_2026-11-03.md`。
