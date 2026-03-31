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

OpenClaw 集成也可以直接用：

```bash
/Users/rootliu/code/stock-prediction/scripts/run_openclaw_report.sh /path/to/openclaw/stock-prediction
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

- `/Users/rootliu/code/stock-prediction/ml-service/data/external_direction_signal.csv`

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
/Users/rootliu/code/stock-prediction/.venv/bin/python \
  /Users/rootliu/code/stock-prediction/ml-service/backtest/gold_rolling_backtest.py \
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

当前黄金预测默认策略为 `ensemble`，保留两种回退方式：

- `boosting`
- `linear`

### Agent 调用索引

如果需要让其它 agent 直接调用黄金预测流程，优先看这两份文档：

- `docs/GOLD_AGENT_USAGE.md`：黄金预测 agent 调用手册，包含默认参数、回退方式、HTTP API 和输出契约
- `docs/OPENCLAW_INTEGRATION.md`：OpenClaw/cron 无界面巡检接入方式

推荐调用约定：

- 默认粒度使用 `4h`
- 默认模型使用 `ensemble`
- 需要回退时显式指定 `boosting` 或 `linear`
- 机器人模式以下游读取 `manifest.json` 作为完成标记
- 现阶段不要把 `15min/30min` 作为 agent 默认入口
- 如果需要直接产出“汇报版 + 三情景 + 图片”的新黄金报告，优先使用 `scripts/run_gold_direct_report.sh`

最小调用示例：

```bash
/Users/rootliu/code/stock-prediction/scripts/run_openclaw_report.sh /tmp/agent-gold-report
```

新黄金情景报告的最小调用示例：

```bash
/Users/rootliu/code/stock-prediction/scripts/run_gold_direct_report.sh /tmp/gold-direct-agent 2026-04-03
```

需要显式指定模型时：

```bash
OPENCLAW_PREDICT_MODEL=ensemble /Users/rootliu/code/stock-prediction/scripts/run_openclaw_report.sh /tmp/agent-gold-report
OPENCLAW_PREDICT_MODEL=boosting /Users/rootliu/code/stock-prediction/scripts/run_openclaw_report.sh /tmp/agent-gold-report
OPENCLAW_PREDICT_MODEL=linear /Users/rootliu/code/stock-prediction/scripts/run_openclaw_report.sh /tmp/agent-gold-report
```

直接调用 API：

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/gold/predict/SHFE_AU_MAIN \
  -H 'Content-Type: application/json' \
  -d '{"horizon": 5, "lookback": 120, "model_type": "ensemble"}'
```

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
