# Stock Prediction - Architecture Analysis

> Auto-generated on 2026-03-26. Based on codebase exploration.

## Project Overview

AI-powered金融市场预测系统，支持 A 股、港股、黄金市场的数据采集、技术分析、ML 预测和自动报告生成。

**Tech Stack:**
- Frontend: React 18 + TypeScript + Vite + Ant Design + ECharts + Zustand
- Backend: Python FastAPI + AKShare + yfinance + scikit-learn
- Deployment: GUI 模式 (Web) + Bot 模式 (OpenClaw cron 集成)

---

## Directory Structure

```
stock-prediction/
├── client/                          # React 前端
│   └── src/
│       ├── components/
│       │   ├── KLineChart.tsx       # K 线蜡烛图 (ECharts)
│       │   ├── GoldTrendChart.tsx   # 黄金预测趋势图
│       │   ├── StockList.tsx        # 股票列表 + 搜索
│       │   └── IndexBar.tsx         # 大盘指数显示
│       ├── services/api.ts          # Axios API 客户端
│       ├── store/index.ts           # Zustand 状态管理
│       ├── types/index.ts           # TypeScript 类型定义
│       └── App.tsx                  # 主应用 (A股/港股/黄金切换)
│
├── ml-service/                      # Python 后端
│   ├── main.py                      # FastAPI 服务 + 全部 API 端点
│   ├── data_collector/
│   │   ├── a_stock.py               # A 股数据采集 (AKShare)
│   │   ├── hk_stock.py              # 港股数据采集 (AKShare)
│   │   ├── gold_market.py           # 黄金多源采集 (SHFE/COMEX/LBMA/ETF)
│   │   └── __init__.py              # 单例工厂
│   ├── models/
│   │   ├── predictor.py             # 价格预测 (ensemble/boosting/linear)
│   │   └── external_direction.py    # 外部市场情绪特征
│   ├── utils/indicators.py          # 技术指标 (MA/MACD/RSI/KDJ/BOLL 等)
│   ├── backtest/
│   │   └── gold_rolling_backtest.py # 滚动回测 (Walk-Forward)
│   ├── reporting/
│   │   ├── bot_report.py            # Bot 模式报告生成
│   │   └── external_gold_consensus.py # 外部共识曲线
│   └── data/                        # 外部信号数据
│
├── scripts/
│   ├── run_openclaw_report.sh                  # OpenClaw wrapper
│   └── generate_gold_4h_dailyclose_report.py   # 4H 日收报告脚本
│
├── docs/                            # 项目文档
├── run.py                           # 统一启动器 (GUI/Bot)
└── run_gold_analysis.py             # 黄金分析独立脚本
```

---

## API Endpoints

### A 股 `/api/v1/a-stock/`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/list` | 全部 A 股列表 |
| GET | `/quote/{symbol}` | 实时行情 |
| POST | `/quotes` | 批量行情 |
| GET | `/kline/{symbol}` | K 线数据 (日/周/月) |
| GET | `/index/{code}` | 大盘指数 (上证/深证/创业板) |
| GET | `/north-flow` | 北向资金 |
| GET | `/sectors` | 行业板块 |

### 港股 `/api/v1/hk-stock/`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/list` | 全部港股列表 |
| GET | `/quote/{symbol}` | 实时行情 |
| POST | `/quotes` | 批量行情 |
| GET | `/kline/{symbol}` | K 线数据 |
| GET | `/hsi` | 恒生指数 |
| GET | `/south-flow` | 南向资金 |
| GET | `/hot` | 热门股票 |
| GET | `/ggt` | 港股通标的 |

### 黄金 `/api/v1/gold/`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sources` | 可用数据源 |
| GET | `/markets` | 市场分组 (国内/国际/夜盘) |
| GET | `/quote/{source}` | 最新报价快照 |
| GET | `/kline/{source}` | K 线 (daily/4h/5min~60min/weekly/monthly) |
| GET | `/compare` | 多源对比 (收盘价对齐) |
| GET | `/session/{source}` | 白盘/夜盘拆分数据 |
| POST | `/predict/{source}` | **价格预测** |

### 技术指标 `/api/v1/indicators/`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/` | 批量计算指标 |
| GET | `/{symbol}` | 获取最新指标 |

---

## ML Prediction Pipeline

### Model Types

| Type | Algorithm | Characteristics |
|------|-----------|----------------|
| **linear** | LinearRegression + LogisticRegression | 保守基线，低方差 |
| **boosting** | GradientBoosting (Regressor + Classifier) | 激进，支持外部方向特征 |
| **ensemble** | linear + boosting 加权融合 | **生产默认**，平衡准确性与稳定性 |

### Feature Engineering

```
Lag features:     lag_1, lag_2, lag_3, lag_5
Return features:  ret_1, ret_3, ret_5
Moving averages:  ma_5, ma_10, ma_20, ma_gap_5/10/20
Volatility:       vol_5 (5 日滚动标准差)
External (可选):  ext_dir_level, ext_dir_ema_5/20, ext_dir_delta_3,
                  ext_conf_level, ext_stance_dispersion
```

### Prediction Flow

```
Input DataFrame (date + close)
  ↓
_build_feature_frame()          # 特征工程
  ↓
Train/Test Split (lookback)
  ↓
┌─────────────────────────────────────┐
│  ensemble mode:                      │
│  ├─ Linear model → pred_linear      │
│  ├─ Boosting model → pred_boosting  │
│  └─ Weighted blend + ext constraint │
│     → final prediction              │
└─────────────────────────────────────┘
  ↓
Bias Correction (per volatility regime)
  ↓
Return Clipping (max 2.5x vol or 3%)
  ↓
Output: history, prediction[], metrics{mae, mape, direction_accuracy}
```

### Ensemble Fusion Logic

1. 分别训练 linear 和 boosting 模型
2. 基于 inverse MAPE + direction accuracy 计算权重
3. External direction 仅应用于 boosting 分支
4. 方向冲突时自动裁决 (55-70% dampening)
5. 最终输出经过 bias calibration

---

## Data Sources

| Source | Provider | Coverage |
|--------|----------|----------|
| **SHFE_AU_MAIN** | AKShare (上海期交所) | 国内黄金主力，支持 4h/分钟级 |
| **COMEX** | yfinance | COMEX 黄金期货 |
| **LBMA_SPOT** | yfinance (XAUUSD) | 伦敦现货金 |
| **US_ETF** | yfinance (GLD) | 黄金 ETF |
| **A 股** | AKShare | 全部 A 股实时/历史 |
| **港股** | AKShare | 全部港股实时/历史 |

---

## Frontend Architecture

### 三大视图

1. **A 股视图** — 左侧股票列表 + 自选股，右侧 K 线图 + 行情
2. **港股视图** — 同上布局，港股数据
3. **黄金视图** — 数据源选择 + 预测走势/多源对比/白盘夜盘三个 Tab

### State Management (Zustand)

- `currentMarket`: 'CN' | 'HK' | 'GOLD'
- `currentStock`: 当前选中股票
- `klineData`: K 线数据
- `watchlist`: 自选股列表 (localStorage 持久化)
- `indexes`: 大盘指数

---

## Backtest Framework

`backtest/gold_rolling_backtest.py` 实现 Walk-Forward 滚动回测:

- 滚动窗口 + 可配置 stride 和 horizon
- 输出指标: MAE, RMSE, MAPE, bias, 方向准确率, aggressive ratio
- 支持波动率分区 (高波 vs 正常) regime 分析
- CLI 参数: `--source`, `--period`, `--session`, `--lookback`, `--max-horizon`, `--stride`

---

## Bot / Report Mode

通过 `run.py --bot-output-dir PATH` 进入无头模式，生成完整报告包:

**输出文件 (22 个):**

| Category | Files |
|----------|-------|
| Metadata | `manifest.json` (完成标记) |
| Report | `report.md` |
| Data (JSON/CSV) | `gold_quote.json`, `gold_prediction.json`, `gold_history.csv`, `gold_forecast.csv`, `gold_compare.csv`, `gold_session.csv`, `external_gold_survey.csv`, `gold_curve_comparison.csv`, `gold_external_main_curve.csv` |
| Charts (PNG) | `gold_prediction.png`, `gold_compare.png`, `gold_session.png`, `gold_curve_comparison.png` |
| Tables (PNG) | `gold_summary_table.png`, `gold_forecast_table.png`, `gold_external_survey_table.png`, `gold_curve_comparison_table.png` |

---

## Development Phases

| Phase | Status | Content |
|-------|--------|---------|
| 1. 数据采集 | Done | A 股/港股/黄金多源数据采集 |
| 2. K 线 + 技术指标 | Done | ECharts K 线图 + MA/MACD/RSI/KDJ/BOLL |
| 3. 预测模型 | Done | Linear/Boosting/Ensemble + 外部情绪 |
| 4. 回测系统 | Done | Walk-Forward 滚动回测 |
| 5. 集成优化 | In Progress | OpenClaw 集成、MAG7 规划中 |

---

## Quick Start

```bash
# GUI 模式 (前后端同时启动)
cd stock-prediction
python run.py

# Bot 模式 (生成报告)
python run.py --bot-output-dir /tmp/gold-report --predict-model ensemble

# 仅后端
cd ml-service && python main.py

# 仅前端
cd client && npm run dev
```
