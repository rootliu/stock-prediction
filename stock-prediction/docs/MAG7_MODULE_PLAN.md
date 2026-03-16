# 美股七巨头模块计划与设计（独立模块）

## 1. 模块目标

七巨头模块独立于黄金模块，聚焦：

1. 七巨头行情与 K 线数据
2. 单标的预测与批量预测
3. 七巨头对比可视化输出

股票池固定：
- `AAPL`, `MSFT`, `AMZN`, `GOOGL`, `META`, `NVDA`, `TSLA`

## 2. 模块边界

输入：
- 股票代码（限定在七巨头池）
- 周期参数（daily/weekly/monthly）
- 预测参数（horizon/lookback）

输出：
- 标准化行情与 K 线
- 单标的预测结果
- 批量预测摘要（未来 N 日预期涨跌幅）

## 3. 后端结构设计

规划新增：

```text
ml-service/
  data_collector/
    us_stock.py
  models/
    predictor.py           # 与黄金模块共享预测器
```

规划 API：
- `GET /api/v1/us-stock/mag7/list`
- `GET /api/v1/us-stock/quote/{symbol}`
- `GET /api/v1/us-stock/kline/{symbol}`
- `POST /api/v1/us-stock/predict/{symbol}`
- `POST /api/v1/us-stock/mag7/predict-batch`

## 4. 执行顺序

当前状态：
- 本模块暂未开始实现
- 先完成黄金模块（当前进行中）

下一步（黄金完成后）：
1. 数据采集器 `us_stock.py`
2. API 路由与预测接口
3. 前端七巨头对比页面

---

免责声明：预测结果仅用于研究与学习，不构成投资建议。
