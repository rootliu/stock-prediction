# 黄金 + 美股七巨头预测功能实施计划

## 1. 目标

在现有 `stock-prediction` 系统中新增两条能力：

1. 黄金走势预测（整合多个主流交易场所/市场来源的数据）
2. 美国七大科技股（Magnificent 7）走势预测与可视化

并在前端提供历史走势 + 预测走势的图表展示。

## 2. 范围定义（V1）

### 2.1 黄金数据范围

- 支持多来源数据聚合（统一格式输出）：
  - `COMEX`: `GC=F`（CME/COMEX 黄金期货）
  - `LBMA_SPOT`: `XAUUSD=X`（现货金价格代理）
  - `US_ETF`: `GLD`（美股黄金 ETF，流动性高）
- 提供来源间价差/偏离度对比（仅分析，不做套利建议）

### 2.2 美股七巨头范围

- 固定股票池：
  - `AAPL`, `MSFT`, `AMZN`, `GOOGL`, `META`, `NVDA`, `TSLA`
- 功能：
  - 历史行情查询（OHLCV）
  - 单标的预测
  - 七巨头批量预测（排行榜/热力摘要）

## 3. 技术设计

### 3.1 后端（ml-service）改造

新增目录：

```text
ml-service/
  data_collector/
    gold_market.py
    us_stock.py
  models/
    predictor.py
  utils/
    features.py
```

设计原则：

- 与现有 `a_stock.py` / `hk_stock.py` 保持一致的数据层风格
- 新增接口继续放在 `ml-service/main.py`
- 所有返回结构对齐现有 `KLineResponse` 风格，降低前端改造成本

### 3.2 数据获取策略

- 统一以 `yfinance` 为 V1 主数据源（项目依赖中已包含）
- 对每个来源实现独立抓取器，聚合后做标准化：
  - 列标准：`date/open/high/low/close/volume/source/symbol`
- 预留二级数据源（AKShare/交易所公开接口）作为后续增强

### 3.3 预测策略（V1）

- 先上可解释、可稳定运行的基线模型，不直接上复杂深度学习：
  - 模型：`XGBoostRegressor`（或 LightGBM）
  - 目标：预测未来 `N` 日收盘价（默认 5 日）
  - 特征：
    - 滞后收益率（1/3/5/10）
    - 均线偏离（MA5/10/20）
    - 波动率（rolling std）
    - 成交量变化率
- 输出：
  - 预测价格序列
  - 基线误差指标（MAE / MAPE，基于时间切分回测）

## 4. API 设计（新增）

### 4.1 黄金

- `GET /api/v1/gold/sources`
  - 返回可用来源与符号映射
- `GET /api/v1/gold/kline/{source}`
  - 查询历史 K 线，参数：`period/start_date/end_date`
- `GET /api/v1/gold/compare`
  - 多来源同周期对齐比较
- `POST /api/v1/gold/predict/{source}`
  - 请求体：`horizon`, `lookback`, `model`
  - 返回历史序列 + 预测序列 + 评估指标

### 4.2 美股七巨头

- `GET /api/v1/us-stock/mag7/list`
- `GET /api/v1/us-stock/quote/{symbol}`
- `GET /api/v1/us-stock/kline/{symbol}`
- `POST /api/v1/us-stock/predict/{symbol}`
- `POST /api/v1/us-stock/mag7/predict-batch`
  - 返回七只股票预测摘要（未来 5 日预期涨跌幅）

## 5. 前端改造计划（client）

### 5.1 信息架构

- 顶部市场维度扩展：
  - `A股` / `港股` / `黄金` / `美股七巨头`
- 新增两个页面组件：
  - `GoldDashboard.tsx`
  - `USMag7Dashboard.tsx`

### 5.2 图表能力

- 复用 `KLineChart.tsx`，增加 `predictionSeries` 叠加线
- 统一图例：
  - 历史价格（K 线或收盘线）
  - 预测价格线
  - 置信区间带（V2，可选）
- 七巨头页额外增加：
  - 批量预测对比图（7 条折线/柱状预期涨跌）

### 5.3 API 与类型

- `client/src/types/index.ts` 新增：
  - `AssetType`, `PredictionPoint`, `PredictionResponse`
- `client/src/services/api.ts` 新增：
  - `goldApi`
  - `usStockApi`

## 6. 分阶段执行与验收

### Phase A: 数据层落地（1-2 天）

- 交付：
  - `gold_market.py`, `us_stock.py`
  - 基础行情接口可返回数据
- 验收：
  - 黄金三来源均可成功返回最近 90 天数据
  - 七巨头全部可返回日 K

### Phase B: 预测层落地（2 天）

- 交付：
  - `models/predictor.py`
  - 黄金/美股预测 API
- 验收：
  - 能返回未来 5 日预测
  - 返回 MAE/MAPE 指标

### Phase C: 前端图表与交互（2 天）

- 交付：
  - 黄金页 + 七巨头页
  - 预测曲线叠加
- 验收：
  - 可切换标的、周期并刷新预测
  - 图表无阻塞报错（空数据处理完整）

### Phase D: 稳定性与文档（1 天）

- 交付：
  - 错误处理、限流、缓存（基础）
  - README 与接口文档更新
- 验收：
  - 常见失败场景可返回清晰错误信息
  - 文档可指导本地启动与调试

## 7. 风险与应对

- 数据源不稳定：
  - 增加超时与重试；来源失效时降级到其他来源
- 美股时区与交易日差异：
  - 统一使用 UTC 存储 + 前端本地化展示
- 预测误差偏大：
  - V1 明确为基线模型；V2 再引入 LSTM/Transformer

## 8. 立即执行清单（下一步）

1. 先实现 `Phase A`（数据层 + 基础 API）
2. 接着实现 `Phase B`（预测 API）
3. 最后做前端图表与交互联调

---

免责声明：本系统预测结果仅用于技术研究与学习，不构成任何投资建议。
