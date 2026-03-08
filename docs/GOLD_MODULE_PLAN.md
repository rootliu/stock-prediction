# 黄金模块计划与设计（独立模块）

## 1. 模块目标

黄金模块独立于 A 股/港股/美股模块，负责：

1. 聚合国内、国外和夜盘三个维度的黄金市场数据
2. 提供统一的日线/分时走势与跨市场对比接口
3. 提供黄金价格短期预测接口
4. 在前端提供清晰的折线图、对比图和时段图展示

## 2. 模块边界

输入：
- 数据源标识（国内 / 国外 / 具体品种）
- 时间周期参数（`daily` / `5min` / `15min` / `60min` / `weekly` / `monthly`）
- 时段参数（`ALL` / `DAY` / `NIGHT`）
- 预测参数（`horizon`、`lookback`）

输出：
- 标准化价格结构（`date/open/high/low/close/volume/session`）
- 多来源对比序列
- 国内/国外/夜盘分段走势序列
- 预测序列与误差指标（MAE/MAPE）

不包含（V1）：
- 自动交易
- 套利策略
- 宏观因子模型

## 3. 数据源设计

### 3.1 国外市场

V1 已接入并继续保留：
- `COMEX` -> `GC=F`（CME/COMEX 黄金期货）
- `LBMA_SPOT` -> `XAUUSD=X`（现货金代理）
- `US_ETF` -> `GLD`（黄金 ETF）

### 3.2 国内市场

V2 规划接入：
- `SHFE_AU_MAIN`：上期所黄金主力合约
- `SHFE_AU9999` 或可替代国内黄金连续合约
- `CN_GOLD_ETF`：国内黄金 ETF（作为行情补充与前端参考锚点）

优先方案：
- 通过 `AKShare` 获取国内黄金期货 / ETF 日线与分时数据
- 若部分品种分钟级数据不足，再补 `Tushare` 或交易所公开接口

### 3.3 夜盘数据

夜盘不是独立市场，而是国内黄金期货的独立交易时段，需要从分钟级数据里切分：
- `DAY`：国内白天交易时段
- `NIGHT`：国内夜盘交易时段
- `ALL`：合并全时段

核心原则：
- 底层存储使用统一时间序列
- API 返回时附带 `session` 字段
- 前端根据 `session` 做图形切换和着色

统一规范：
- 列名统一为小写标准列
- 日期统一为 `datetime`
- 时区统一存储，前端按本地时区展示
- 缺失值统一清洗并按日期升序

## 4. 后端结构设计

新增文件：

```text
ml-service/
  data_collector/
    gold_market.py        # 黄金数据采集器（独立）
  models/
    predictor.py          # 预测基线模型（可复用）
```

API 放置在：
- `ml-service/main.py` 的 `gold` 路由段

## 5. API 设计（gold 独立命名空间）

- `GET /api/v1/gold/sources`
  - 列出可用来源与符号映射

- `GET /api/v1/gold/markets`
  - 列出国内 / 国外 / 夜盘视图及可用来源

- `GET /api/v1/gold/quote/{source}`
  - 返回单来源最新行情快照

- `GET /api/v1/gold/kline/{source}`
  - 参数：`period/start_date/end_date/session`
  - 返回标准 K 线

- `GET /api/v1/gold/compare`
  - 参数：`period/start_date/end_date/group/session`
  - 返回多来源对齐后的价格序列

- `GET /api/v1/gold/session/{source}`
  - 参数：`date/period`
  - 返回同一来源按 `DAY/NIGHT` 切分后的走势数据

- `POST /api/v1/gold/predict/{source}`
  - 请求体：`horizon`, `lookback`, `session`
  - 返回：历史收盘 + 未来预测 + 评估指标

## 6. 预测方案（V1）

- 模型：`LinearRegression`（稳定、可解释、依赖轻）
- 特征：
  - 滞后价格（1/2/3/5）
  - 滞后收益率（1/3/5）
  - MA（5/10/20）及偏离率
  - 5 日波动率
- 输出：
  - 未来 N 日预测值
  - MAE/MAPE（时间切分验证）

V2 增强：
- 国内夜盘与白盘分开训练，避免把两个时段的波动结构混在一起
- 增加跨市场特征：
  - 国内 AU 与 COMEX 收益差
  - 美元金价变动
  - ETF 资金流代理特征
  - 夜盘开盘跳空幅度

## 7. 交付拆分

Phase G1（当前）：
- 完成 `gold_market.py`
- 完成 gold API（sources/quote/kline/compare/predict）
- 完成基础前端日线图（实际/预测双色折线）

Phase G2：
- 接入国内黄金数据
- 增加国内 / 国外切换与对比图

Phase G3：
- 接入分钟级时序与夜盘切分
- 增加夜盘走势视图与时段过滤
- 预测接口支持 `session=DAY/NIGHT/ALL`

Phase G4：
- 强化模型（XGBoost/LSTM）
- 置信区间与风险标注

## 8. 前端图形规划

默认不使用 K 线作为黄金主视图，采用更适合跨市场比较的折线图：

1. 主图：日线实际价格 vs 预测价格
   - 实际线：实线
   - 预测线：虚线

2. 对比图：国内 vs 国外
   - 同一时间轴双线或多线对比
   - 支持价格归一化，便于观察相对强弱

3. 时段图：白盘 vs 夜盘
   - 同一来源按 session 分色
   - 支持最近 1 日 / 5 日 / 20 日切换

4. 差值图：
   - 国内 AU 与 COMEX / XAUUSD 的价差曲线
   - 用于辅助理解联动与偏离，不作为套利建议

---

免责声明：预测结果仅用于研究与学习，不构成投资建议。
