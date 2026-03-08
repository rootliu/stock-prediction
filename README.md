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

## ✨ 功能特性

- 📊 K线图表（支持日/周/月K线切换）
- 📈 技术指标（MA、MACD、RSI、布林带等）
- 💰 A股和港股实时行情
- ⭐ 自选股管理
- 🔔 买卖信号提示
- 🤖 AI 预测模型
- 📉 回测系统

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
</content>
<parameter name="task_progress">
- [ ] Phase 1: 项目初始化 + 数据采集
  - [x] 创建项目目录结构
  - [x] 创建项目需求文档
  - [x] 初始化Python数据采集服务
  - [x] 初始化前端React项目
  - [ ] 创建启动脚本和README
    - [x] 创建postcss配置
    - [x] 创建README文档
- [ ] Phase 2: K线图表 + 技术指标
- [ ] Phase 3: 预测模型训练
- [ ] Phase 4: 回测系统
- [ ] Phase 5: 集成优化
