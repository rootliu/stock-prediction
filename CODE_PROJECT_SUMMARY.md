# /Users/rootliu/code 项目扫描总结

- 扫描时间: 2026-03-08
- 扫描范围: `/Users/rootliu/code` 一级目录中的项目型文件夹 + 根目录脚本/文档/资产
- 识别到的项目数: 3

## 项目总览

| 项目 | 类型 | 主要技术栈 | 当前状态 |
|---|---|---|---|
| `pan_cleaner` | 网盘文件清理 Web 应用 | Flask + 原生前端 + Supabase + Vercel | 功能较完整，百度网盘可用 |
| `stock-prediction` | 股票分析系统（前后端+ML） | React + TypeScript + FastAPI + AKShare/yfinance | 早期开发中，黄金模块已开始落地 |
| `pytorchTutorial` | 教程/学习代码集 | PyTorch + Python | 教学脚本集合，非产品型项目 |

## 1) pan_cleaner

### 目标与定位
- 网盘文件清理工具，核心是扫描并清理重复文件/大文件/可执行文件。
- 目前以百度网盘为主，阿里云盘和夸克网盘接口已预留但未实现。

### 结构与实现
- 后端入口: `app.py`（Flask 路由和业务主流程）
- 核心模块: `core/`（Provider 抽象、重复检测、分析、清理）
- 前端: `templates/` + `static/`（无前端框架）
- 持久化与会话: `utils/supabase_client.py` + Supabase 表
- 部署: `vercel.json`（Serverless）

### 成熟度评估
- 优势:
  - 功能链路完整（登录、扫描、分析、清理、报告）。
  - 对 serverless 场景做了会话恢复和缓存设计。
- 待完善:
  - 多网盘能力尚未落地（阿里云盘/夸克仍为占位实现）。
  - 登录方式以 Cookie 为主，其他方式未完成。

## 2) stock-prediction

### 目标与定位
- 面向 A 股/港股的行情分析与预测平台，包含前端展示、数据服务与机器学习服务。

### 结构与实现
- 前端: `client/`（React + TS + AntD + ECharts + Zustand）
- ML 服务: `ml-service/`（FastAPI，A股/港股采集、K 线与指标 API）
- 文档: `docs/REQUIREMENTS.md`
- 当前新增: 黄金模块数据采集、预测接口、前端日线预测图
- 仍为空或未落地: `server/`、`ml-service/backtest/`

### 成熟度评估
- 已完成:
  - 前端页面骨架和核心交互（列表、搜索、K 线展示、自选股）。
  - FastAPI 接口与数据采集代码（AKShare 驱动）。
  - 黄金模块已拆分为独立模块，后端支持 `sources/quote/kline/compare/predict`，前端提供日线实际/预测双色折线图。
- 尚未完成:
  - Node 后端未实际实现（目录为空）。
  - 七巨头模块仍停留在规划文档阶段，尚未落代码。
  - 回测模块尚未落地。
  - 依赖较重（如 `ta-lib`）且部署复杂度较高。

## 3) pytorchTutorial

### 目标与定位
- PyTorch 入门教程代码仓，按章节脚本演进（张量、自动求导、CNN、迁移学习等）。

### 结构与实现
- 多个编号脚本文件（`02_tensor_basics.py` 到 `19_torch_compile.py` 等）
- 配套数据与幻灯片目录（`data/`, `slides/`）
- `23_resnet.py` 当前为空文件

### 成熟度评估
- 优势:
  - 内容覆盖面广，适合学习与教学。
- 限制:
  - 不是统一可部署应用，偏脚本演示。
  - 部分章节可能未补全（如空文件）。

## 根目录补充观察

- 顶层 Git 仓库存在: `/Users/rootliu/code/.git`
- 子仓库存在: `/Users/rootliu/code/pan_cleaner/.git`
- 根目录是混合工作区，不只包含项目，还包括文档、图表、脚本、配置和个人资产。

## 根目录文件分类

### 1) 独立静态网页
- `snake/index.html` + `snake/script.js` + `snake/style.css`
- 内容是一个独立的贪吃蛇小游戏，不属于现有三大项目中的任何一个。
- 规模较小，更像单文件练习或临时 Demo。

### 2) 研究与文档资产
- `report/research-agentic-ai-infrastructure.md`
- `report/ecommerce-ad-bidding-flow.drawio`
- `report/ecommerce-click-through-ad-flow.drawio`
- `report/ecommerce-ad-bidding-flow.drawio.png`
- 这些文件属于研究资料和流程设计资产，不是可执行应用。

### 3) 自动化/集成脚本
- `unity_report_to_feishu.py`
- `unity_report_merged.py`
- 两个脚本都在操作飞书文档 API，作用是把 Unity 研究报告写入飞书文档。
- 这类文件属于一次性内容发布或内部自动化脚本，不是完整产品工程。

### 4) 配置与个人资产
- `config.yaml`
- `tokyo.yaml`
- `CordCloud_Clash_1700098418_副本.yaml`
- `setup_openvpn.sh`
- `liujiyao 体检2023 肥胖.pdf`
- 这些文件明显偏向个人配置、网络环境和私有资料，应与项目代码隔离管理。

## 新增风险观察

- `unity_report_to_feishu.py` 与 `unity_report_merged.py` 中包含硬编码的飞书 `APP_ID`、`APP_SECRET` 和 `DOC_ID`。
- 这是明确的凭据泄露风险。如果该目录进入共享仓库或被误传，凭据可能被直接滥用。
- 建议将这类敏感信息迁移到环境变量或本地未纳入版本控制的配置文件。

## 当前工作区结构判断

- `pan_cleaner` 是完成度最高、最接近独立产品的项目。
- `stock-prediction` 是当前最活跃的开发项目，近期主要新增集中在黄金预测模块。
- `pytorchTutorial` 是学习型代码仓。
- `report/` 与 `snake/` 已开始承担工作区整理作用，但根目录仍然混合了较多脚本、配置和私有资产。

## 优先级建议

1. 若目标是“可上线产品”，优先投入 `pan_cleaner`，补齐多网盘 Provider。
2. 若目标是“量化/行情平台”，继续推进 `stock-prediction` 的黄金模块完善，再补齐七巨头模块、回测与 `server` 实现。
3. 当前已完成 `report/` 和 `snake/` 的第一步整理，下一步建议继续把根目录脚本、配置和个人资料迁移到更清晰的子目录，例如 `scripts/`、`private/`。
4. `pytorchTutorial` 作为学习资源保留即可，建议单独归档到 `learning/` 类目录，避免与产品项目混杂。
