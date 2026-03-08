# 中国A股 & 港股预测分析系统

## 项目概述
基于AI/机器学习的中国A股和港股预测分析系统，提供实时行情、技术分析、AI预测和策略回测功能。

## 技术栈

### 前端
- React 18 + TypeScript
- Ant Design 5.x (UI组件库)
- ECharts (K线图表)
- Zustand (状态管理)
- Vite (构建工具)

### 后端 (Node.js)
- Express.js
- WebSocket (实时行情推送)
- PostgreSQL (关系数据库)
- Redis (缓存)

### 机器学习服务 (Python)
- FastAPI (API框架)
- AKShare (A股数据)
- PyTorch (深度学习)
- Pandas/NumPy (数据处理)
- Backtrader (回测框架)

## 核心功能

### 1. 数据采集
- A股实时/历史行情 (AKShare)
- 港股数据 (AKShare/富途)
- 财务数据
- 北向资金流向
- 龙虎榜数据

### 2. 技术分析
- K线图表 (日/周/月/年)
- 技术指标 (MA/MACD/RSI/KDJ/BOLL)
- 形态识别
- 支撑/阻力位

### 3. AI预测
- LSTM时间序列预测
- 多因子模型
- 情绪分析

### 4. 策略回测
- 历史数据回测
- 收益分析
- 风险评估

## 开发阶段

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 1 | 项目初始化 + 数据采集 | 进行中 |
| Phase 2 | K线图表 + 技术指标 | 待开始 |
| Phase 3 | 预测模型训练 | 待开始 |
| Phase 4 | 回测系统 | 待开始 |
| Phase 5 | 集成优化 | 待开始 |

## 风险提示
⚠️ 股市有风险，预测仅供参考，不构成投资建议