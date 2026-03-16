# AI Coding 技术综述 — Workshop 参考资料

> 基于论文:
> - *"From Code Foundation Models to Agents and Applications: A Comprehensive Survey and Practical Guide to Code Intelligence"* (2511.18538, 303页, 2025)
> - *"AI Agentic Programming: A Survey of Techniques, Challenges, and Opportunities"* (2508.11126, 36页, 2025)

---

## 一、AI Coding 的历史与发展阶段

> 📊 图表: [AI Coding 发展历程](./diagrams/ai_coding_evolution.drawio)

### 1.1 发展阶段概览

| 阶段 | 时间 | 核心特征 | 代表性成果 |
|------|------|---------|-----------|
| **规则与符号系统** | 1960s - 2016 | 形式化规范、符号搜索、领域特定 | 程序综合 (Program Synthesis)、逻辑编程 |
| **Transformer 革命** | 2017 - 2020 | 注意力机制、预训练范式、规模化 | Transformer (2017)、GPT-1/2/3 |
| **代码专用大模型** | 2021 - 2022 | 代码预训练、商业化IDE集成 | Codex、GitHub Copilot、AlphaCode、StarCoder |
| **指令对齐与推理** | 2023 - 2024 | RLHF/SFT对齐、链式推理、开源追赶 | GPT-4、Claude、DeepSeek-Coder、CodeLlama |
| **Agent 自主编程** | 2025+ | 多步规划、工具调用、自主决策 | Claude Code、Cursor Agent、GPT-5 Codex、Devin |

### 1.2 关键里程碑

- **2017**: Transformer 架构发表，"从根本上重新概念化了问题空间"
- **2020**: GPT-3 展示零样本/少样本代码生成能力
- **2021.06**: GitHub Copilot 发布 — "开创性的商业化 IDE 集成 AI 编程助手"
- **2021**: Codex 发布，引入 HumanEval 基准测试
- **2023**: GPT-4 带来高级推理能力；StarCoder、CodeLlama 开源模型涌现
- **2024**: DeepSeek-R1 用强化学习实现链式推理；o1/o3 系列引入"内部深思"
- **2025**: GPT-5 Codex — "迄今最强编码模型"；Qwen3-Coder (480B MoE)；Agent 时代全面开启

### 1.3 性能飞跃

HumanEval 基准测试成绩: **从个位数 → 超过 95%**

这一飞跃经历了从规则方法到统计方法，再到深度学习和大语言模型的根本性转变。

### 1.4 系统演进类比

从操作系统的演进视角理解 AI Coding 的发展:

| OS 概念 | AI Coding 类比 | 特征 |
|---------|---------------|------|
| 进程 (Process) | 程序综合 | 主动执行单元 |
| 线程 (Thread) | 代码补全 | 轻量级并发 |
| 对象 (Object) | LLM 助手 | 被动封装 |
| 活跃对象 (Active Object) | 编程 Agent | 自有控制线程、异步消息 |

---

## 二、AI Coding 的技术领域全景

> 📊 图表: [AI Coding 技术全景图](./diagrams/ai_coding_taxonomy.drawio)

### 2.1 编程基础大模型

#### 通用大语言模型 (General LLMs)

具备代码能力的通用模型:

| 模型系列 | 提供方 | 特点 |
|---------|--------|------|
| GPT-4 / GPT-5 | OpenAI | 最强综合推理能力 |
| Claude 系列 | Anthropic | 长上下文、安全对齐 |
| Gemini | Google | 多模态、大上下文窗口 |
| LLaMA 系列 | Meta | 开源领头羊 |
| DeepSeek-V3/R1 | DeepSeek | MoE架构、RL推理 |
| Grok | xAI | 实时信息接入 |

**架构演进方向**:
- **Dense Models**: 传统全参数模型
- **MoE (混合专家)**: DeepSeek-V3, Qwen3-Coder (480B总参/35B激活)
- **循环模型**: RWKV, Mamba — 线性复杂度
- **扩散模型**: Mercury Coder, Gemini Diffusion, DiffuCoder — 非自回归生成
- **混合架构**: Jamba, Qwen3-Next — 注意力 + 状态空间

#### 代码专用大模型 (Code LLMs)

专门针对代码训练或微调的模型:

| 模型 | 参数量 | 提供方 | 特点 |
|-----|--------|--------|------|
| StarCoder / StarCoder2 | 3B - 15B | BigCode | 开源、多语言 |
| CodeLlama | 7B - 34B | Meta | 基于 LLaMA，支持 FIM |
| DeepSeek-Coder V2 | 16B / 236B (MoE) | DeepSeek | 高性能开源 |
| Qwen2.5-Coder | 7B - 32B | 阿里 | 中文友好 |
| Qwen3-Coder | 480B (MoE, 35B active) | 阿里 | 1M上下文, YaRN |
| Codestral | 22B | Mistral | 专注代码 |
| Granite Code | 3B - 34B | IBM | 企业级 |
| Seed-Coder | - | ByteDance | 字节跳动出品 |

### 2.2 IDE 编程助手 (Interactive Code Assistants)

反应式、通常为单轮交互、集成在 IDE 中:

| 产品 | 类型 | 特点 |
|------|------|------|
| **GitHub Copilot** | IDE 插件 | 日处理 ~1.5亿 代码建议；Pro+ 支持 Claude Opus 4 和 GPT-5 |
| **Cursor** | IDE | 2年内 ARR 超 $5亿；200K token 上下文；每秒 100万+ 查询 |
| **TRAE** | IDE | 字节跳动出品 |
| **Windsurf** | IDE | 前 Codeium，专注 AI-first 编辑器 |
| **Tabnine** | IDE 插件 | 企业私有化部署 |
| **CodeGeeX** | IDE 插件 | 智谱出品 |
| **Amazon Q Developer** | 云原生 | AWS 生态集成 |
| **Google Gemini Code Assist** | 云原生 | GCP 生态集成 |
| **通义灵码** | 云原生 | 阿里云生态 |

### 2.3 自主编程 Agent (Autonomous Coding Agents)

主动式、多轮交互、工具增强、自适应:

| 产品/系统 | 类型 | 特点 |
|----------|------|------|
| **Claude Code** | 终端 Agent | Anthropic 出品；MCP 协议；可组合工具定义 |
| **Aider** | 终端 Agent | 开源；支持多模型 |
| **Gemini CLI** | 终端 Agent | Google 出品 |
| **Devin** | 云端 Agent | Cognition；全自主开发环境 |
| **Google Jules** | 云端 Agent | 异步任务处理 |
| **GPT-5 Codex** | 云端 Agent | OpenAI；RL训练的代理编码 |

**Agent 与 Assistant 的关键区别**:

| 维度 | IDE 助手 | Agent |
|------|---------|-------|
| 主动性 | 反应式 (Reactive) | 主动式 (Proactive) |
| 交互轮次 | 单轮 | 多轮迭代 |
| 工具使用 | 有限 | 深度集成编译器/调试器/测试框架/VCS |
| 适应性 | 固定工作流 | 基于反馈动态调整策略 |
| 自主性 | 需要持续人工引导 | 可自主分解任务、规划执行 |

### 2.4 多 Agent 协作系统

| 系统 | 架构模式 | 特点 |
|------|---------|------|
| **ChatDev** | 模拟软件公司 | CEO/CTO/程序员角色分工 |
| **MetaGPT** | 角色分工 | 多 AI Agent 模拟开发团队 |
| **SWE-Agent** | 架构师/编码/审查 | 共享内存的多 Agent 协作 |
| **AutoCodeRover** | 多文件仓库导航 | 真实代码库上的多 Agent 协调 |
| **AutoGen / CrewAI** | 通用框架 | 跨会话上下文、直接工具交互 |

### 2.5 训练与对齐技术

| 技术 | 说明 | 代表方法 |
|------|------|---------|
| **SFT (监督微调)** | 单轮/多轮对话数据训练 | Evol-Instruct, Self-Instruct |
| **RLHF** | 基于人类反馈的强化学习 | InstructGPT, ChatGPT |
| **GRPO** | 分组相对策略优化 | DeepSeek-R1 使用 |
| **DAPO** | 解耦裁剪与动态采样 | AIME 上达到 50% |
| **RLVR** | 可验证奖励的强化学习 | 用测试用例/编译器作为确定性反馈 |
| **DPO** | 直接偏好优化 | 无需奖励模型 |

### 2.6 评估基准

| 基准 | 级别 | 说明 |
|------|------|------|
| **HumanEval** | 函数级 | 164个手写编程题，经典基准 |
| **MBPP** | 函数级 | 974个Python编程题 |
| **BigCodeBench** | 函数级 | 大规模代码评估 |
| **LiveCodeBench** | 函数级 | 持续更新，防数据泄露 |
| **SWE-bench** | 项目级 | 真实GitHub Issue修复，500个验证实例 |
| **SWE-bench Live** | 项目级 | 1565个任务，164个仓库 |
| **SWE-Lancer** | 项目级 | 1488个真实UpWork任务，价值~$100万 |
| **Terminal-Bench** | 系统级 | 终端操作评估 |

---

## 三、AI Coding 与软件工程

> 📊 图表: [AI Coding 覆盖软件工程全生命周期](./diagrams/ai_coding_se_lifecycle.drawio)

### 3.1 覆盖软件工程全生命周期

AI Coding 已经不仅仅是"写代码"，而是渗透到软件工程的每个阶段:

#### 需求分析阶段
- **Elicitron**: 自动化需求获取
- **MARE/MAD**: 需求审查与检验
- **PrototypeFlow/DCGen**: 需求建模与原型生成
- **SimUser/UXAgent**: 用户模拟与需求验证

#### 设计与开发阶段
- **程序综合**: AlphaCodium, CodeCoT, Self-Refine, MapCoder
- **端到端开发**: ChatDev, MetaGPT, AgentCoder, OpenHands, HyperAgent
- **Text-to-SQL**: DAIL-SQL, DIN-SQL, MAC-SQL, OmniSQL (20+ 系统)
- **文档生成**: AutoComment, RepoAgent, DocAgent

#### 测试阶段
- 自动测试用例生成
- 变异测试 (Mutation Testing)
- 模糊测试 (Fuzzing)
- 与 pytest, Jest 等框架深度集成

#### 代码审查阶段
- **PR-Agent**: 自动PR审查
- **CodeRabbit**: AI代码审查平台
- **LLM Code Reviewer**: 基于LLM的代码审查

#### 维护与修复阶段
- **故障定位**: AutoFL, AgentFL, SoapFL
- **补丁生成**: RepairLLaMA, ThinkRepair, MORepair (20+ 系统)
- **自动Bug修复**: SWE-Agent 在真实GitHub Issue上验证

### 3.2 Agent 的核心工作循环

AI Coding Agent 遵循一个迭代式工作循环:

```
用户指令 → LLM 推理 → 任务分解 → 工具调用 → 获取反馈 → 迭代优化 → 输出结果
     ↑                                                    |
     └────────────── 人机交互 ←─────────────────────────────┘
```

> 📊 图表: [AI Coding Agent 核心架构](./diagrams/ai_coding_agent_arch.drawio)

核心组件:
1. **LLM 推理核心**: 任务理解、代码生成、决策判断
2. **规划模块**: Chain-of-Thought, ReAct, 伪代码中间表示
3. **上下文管理**: 代码库索引、向量检索、分层记忆 (短期/中期/长期)
4. **工具集成**: 编译器、调试器、测试框架、Linter、Git、构建系统
5. **执行监控**: 编译错误触发修改、测试失败触发调试、Linter警告触发重构

### 3.3 从"辅助编码"到"端到端软件工程"

**当前能力边界**:
- 顶级 AI 系统在多模态推理方面仍有困难 (SWE-bench M)
- 最好的模型在特性实现任务上只能解决约 10% 的案例 (FEA-Bench)
- SWE-Lancer 用真实的 UpWork 任务评估"经济价值创造"而非仅仅"准确率"

**研究趋势**: 从单阶段 Agent → 集成的全生命周期编排系统

### 3.4 对外包软件公司的影响

| 维度 | 影响 | 机遇 |
|------|------|------|
| **开发效率** | 常规编码任务效率提升 3-10x | 将人力释放到架构设计和需求理解 |
| **质量保证** | AI 辅助代码审查、自动测试生成 | 降低缺陷率，提高交付质量 |
| **人才结构** | 初级编码工作被替代风险高 | 培养"AI 编程教练"新角色 |
| **交付模式** | 从人天计费转向价值交付 | 更快的原型验证和迭代周期 |
| **服务范围** | 技术门槛降低 | 拓展到更多垂直领域的解决方案 |
| **竞争壁垒** | 纯编码能力不再是壁垒 | 领域知识 + AI 工程能力成为新壁垒 |

---

## 四、AI Coding 目前的研究重点

### 4.1 强化学习与代码推理

这是当前最活跃的研究方向:

- **RLVR (可验证奖励的RL)**: 利用测试用例和编译器提供确定性反馈，训练模型的代码推理能力
- **过程奖励建模**: 评估中间推理步骤，而非仅评估最终输出
- **代表模型**: DeepSeek-R1, Qwen3-Coder, KAT-Coder, DeepCoder
- **关键发现**: "小模型 + 对齐训练" 可以超过 "大模型 + 无对齐" (InstructGPT的启示)

### 4.2 软件工程 Agent 训练

- **SWE 轨迹微调**: 在Agent交互轨迹上进行监督训练
- **环境反馈RL**: 使用测试结果、CI信号作为强化学习奖励
- **端到端 Agent 训练**: 从需求到部署的完整流程训练

### 4.3 安全与可信

论文指出约 **45% 的AI生成代码包含已知漏洞模式**。四维安全框架:

| 维度 | 研究内容 |
|------|---------|
| **安全预训练** | 数据溯源、许可证合规、训练数据审计、对抗鲁棒性、隐私风险评估 |
| **安全后训练** | 安全SFT、偏好优化、编码安全对齐 |
| **红队测试** | 提示级攻击、语义操纵、Agent工作流攻击 |
| **Agent安全** | 沙箱执行环境、预执行验证、运行时监控、意图锚定 |

### 4.4 新型模型架构

- **扩散模型用于代码生成**: Mercury Coder, Gemini Diffusion, DiffuCoder — 非自回归，可并行生成
- **MoE (混合专家)**: 在保持性能的同时大幅降低推理成本
- **超长上下文**: Qwen3-Coder 支持 1M token 上下文 (YaRN)
- **混合架构**: 注意力 + 状态空间模型 (Jamba, Qwen3-Next)

### 4.5 工具链重塑

> **论文核心观点**: 当前的编程语言、编译器和调试器从根本上是为人类设计的，不适合自主 Agent。Agent 需要结构化的、机器可消费的反馈，而非粗糙的错误信息。

研究方向:
- **编译器改造**: 提供结构化的失败反馈、暴露中间表示 (LLVM IR, MLIR)
- **标准化工具协议**: Anthropic 的 MCP (Model Context Protocol)、IEEE P3394 Agent通信标准
- **Agent感知的编程语言**: 支持意图传达的注解和构造

### 4.6 人机协作

- **混合主动工作流**: 控制权在开发者和 Agent 之间流畅切换
- **中断/恢复支持**: Agent 可以被中断、调整方向后恢复
- **共享状态追踪**: 人和 Agent 对项目状态有一致的理解
- **透明推理**: Agent 解释其决策过程，提供置信度标记

### 4.7 评估体系革新

现有基准的不足:
- HumanEval/SWE-bench 以 Python 为主，缺乏多语言覆盖
- SWE-bench 65% 是函数级、25% 模块级、不到 10% 项目级
- 缺乏多轮交互、工具使用效率、失败恢复能力的评估

新方向:
- **多语言基准**: Multi-SWE-bench (7种语言), SWE-PolyBench (21个项目)
- **经济价值评估**: SWE-Lancer 用真实自由职业任务评估
- **全流程评估**: 覆盖需求-设计-开发-测试-部署的端到端评估

### 4.8 八大未来研究方向 (来自 AI Agentic Programming Survey)

1. **软件兼容性**: 重新设计编译器和工具链以支持 Agent
2. **可扩展记忆**: 分层记忆模型 (短/中/长期)
3. **评估基准**: 多语言、端到端、工具使用效率
4. **人-AI协作**: 混合主动工作流、共享状态
5. **领域专精**: 嵌入式、HPC、形式化验证等垂直领域
6. **安全与信任**: 结构化意图语言、轻量验证、行为审计
7. **多Agent协作**: 原生通信协议、会话管理、冲突解决
8. **系统支持**: 云基础设施、自适应调度、高效检查点

---

## 五、前沿模型编程能力对比 (2026年3月最新)

> 以下数据基于网络搜索，截至2026年3月。各模型的benchmark数据来自官方发布或第三方评测。

### 5.1 GPT-5.4 (OpenAI)

**发布时间**: 2026年3月6日
**定位**: "最强大高效的前沿模型，支持编程、计算机操控、工具搜索和1M上下文"

| 项目 | 详情 |
|------|------|
| 上下文窗口 | **1M tokens** |
| 核心创新 | **首个支持原生计算机操控 (Computer Use) 的通用模型** — 可控制鼠标、键盘、截屏导航 |
| 编码能力 | 整合 GPT-5.3-Codex 编码能力，增强工具协调 |
| 代理编程 | RL 训练的代理编码，支持多步自主工作流 |

**GPT-5 系列编码 Benchmark (Aider 排行榜)**:

| 模型 | Aider (225题) | 成本/次 | 格式正确率 |
|------|--------------|---------|-----------|
| GPT-5 (High reasoning) | **88.0%** | $29.08 | 91.6% |
| GPT-5 (Medium) | 86.7% | $17.69 | 88.4% |
| GPT-5 (Low) | 81.3% | $10.37 | 86.7% |

> GPT-5 在 Aider 排行榜上大幅领先所有竞品 (第二名 o3-pro 84.9%, Gemini 2.5 Pro 83.1%)。

### 5.2 Claude Opus 4.6 (Anthropic)

**发布时间**: 2026年2月5日
**模型 ID**: `claude-opus-4-6`
**定位**: "最智能的 Agent 构建和编码模型"

| 项目 | 详情 |
|------|------|
| 上下文窗口 | 200K (标准) / **1M (Beta)** |
| 最大输出 | 128K tokens |
| 训练数据截止 | 2025年8月 |
| 扩展思考 | 支持 Extended Thinking 和 Adaptive Thinking |

**编码 Benchmark**:

| 基准 | 得分 | 说明 |
|------|------|------|
| SWE-bench Verified | **71.7%** (25次平均) / **81.42%** (优化提示) | 真实GitHub Issue修复 |
| Terminal-Bench 2.0 | **行业第一** | 代理终端操作评估 |
| Aider (Opus 4, 32K thinking) | 72.0% | 225 Exercism 编程题 |
| GDPval-AA | 领先 GPT-5.2 约 144 Elo | 经济价值任务评估 |
| BrowseComp | **行业第一** | 难寻信息检索 |
| Humanity's Last Exam | **所有前沿模型中最高** | 复杂跨学科推理 |

**定价**: $5 / 1M input tokens, $25 / 1M output tokens (比 Opus 4.0 降价约 67%)

**核心优势**: 真实世界代理编程、复杂调试与根因分析、多语言编码、MCP 工具协议生态

### 5.3 GLM-5 (智谱 AI)

**发布时间**: 2026年2月11日
**论文**: "GLM-5: from Vibe Coding to Agentic Engineering" (arxiv: 2602.15763)
**开源协议**: MIT

| 项目 | 详情 |
|------|------|
| 总参数量 | **744B** |
| 激活参数 | **40B** |
| 架构 | MoE + DSA (Decoupled Speculative Attention) |
| 预训练数据 | 28.5T tokens |
| 上下文窗口 | 200K tokens |
| 最大输出 | 128K tokens |

**编码与软件工程 Benchmark**:

| 基准 | 得分 |
|------|------|
| SWE-bench Verified | **77.8%** |
| SWE-bench Multilingual | 73.3% |
| SWE-rebench (2026.01) | 42.1% |
| Terminal-Bench 2.0 | **56.2% / 60.7%** |
| AIME 2026 I | 92.7% |
| GPQA-Diamond | 86.0% |

**核心特色**:
- **ARC 框架**: Agentic + Reasoning + Coding 三位一体
- **SLIME**: 异步 RL 基础设施，用于后训练
- 工具调用、函数调用、结构化 JSON 输出
- 开源模型中最强，接近 Claude Opus 4.6 水平
- **定价**: 通过 Z.ai 平台订阅，起步 $10/月

### 5.4 Kimi K2.5 (月之暗面 Moonshot AI)

**发布时间**: 2026年1月26日
**论文**: arxiv: 2602.02276
**开源协议**: Modified MIT

| 项目 | 详情 |
|------|------|
| 总参数量 | **1T (1万亿)** |
| 激活参数 | **32B** |
| 架构 | MoE (基于 DeepSeek V3 改进)，384个专家，每token激活8个 |
| 注意力机制 | MLA (Multi-head Latent Attention) |
| 上下文窗口 | **256K tokens** |
| 视觉编码器 | MoonViT (400M) |

**编码与软件工程 Benchmark**:

| 基准 | 得分 | vs Claude Opus 4.6 |
|------|------|-------------------|
| SWE-bench Verified | **76.8%** | 71.7% |
| SWE-bench Multilingual | 73.0% | - |
| SWE-bench Pro | 50.7% | - |
| Terminal-Bench 2.0 | 50.8% | - |
| LiveCodeBench v6 | **85.0%** | 64.0% |
| AIME 2025 | **96.1%** | - |

**核心特色**:
- **Agent Swarm**: 可协调最多 **100个子Agent并行工作**，执行多达 **1,500个协调步骤**
- **Visual Coding**: 从 UI 设计稿、Mockup、视频工作流直接生成代码
- Thinking & Instant 模式可配置推理深度
- 原生多模态，预训练于 ~15T 混合视觉+文本 tokens
- **定价**: 输入 $0.60 / 1M tokens

### 5.5 MiniMax M2.5

**发布时间**: 2026年初
**开源协议**: Modified MIT
**GitHub**: `github.com/MiniMax-AI/MiniMax-M2.5`

| 项目 | 详情 |
|------|------|
| 总参数量 | **229B** |
| 架构 | MoE |
| 推理链 | 最大 128K tokens |
| 推理速度 | 100 TPS (Lightning) / 50 TPS (Standard) |
| RL框架 | Forge (CISPO算法，~40x 训练加速) |

**编码与软件工程 Benchmark**:

| 基准 | 得分 | vs Claude Opus 4.6 |
|------|------|-------------------|
| SWE-bench Verified | **80.2%** | 78.9% |
| Multi-SWE-bench | 51.3% | - |
| Droid scaffold | 79.7% | 78.9% |
| OpenCode scaffold | 76.1% | 75.9% |

**核心特色**:
- **10+ 编程语言**: Go, C, C++, TypeScript, Rust, Kotlin, Python, Java, JavaScript, PHP, Lua, Dart, Ruby
- **全栈开发**: Web, Android, iOS, Windows
- **Spec优先**: 编码前自动分解特性、结构和UI设计 (架构师式规划)
- MiniMax 内部 30% 任务由 Agent 自主完成，80% 新代码由 M2.5 生成
- **定价**: 输入 $0.30 / 1M tokens, 输出 $2.40 / 1M tokens (Lightning)

> MiniMax M2.5 以 229B 参数量实现了 SWE-bench Verified 80.2%，超过 Claude Opus 4.6 的 78.9%，且成本仅为其 1/10 ~ 1/20。

### 5.6 前沿模型编程能力综合对比

#### SWE-bench Verified (真实GitHub Issue修复能力)

| 模型 | SWE-bench Verified | 参数架构 | 开源 |
|------|-------------------|---------|------|
| **MiniMax M2.5** | **80.2%** | 229B MoE | Yes |
| **GLM-5** | **77.8%** | 744B MoE (40B active) | Yes |
| **Kimi K2.5** | **76.8%** | 1T MoE (32B active) | Yes |
| Claude Opus 4.6 | 71.7% ~ 81.4% | 未公开 | No |
| GPT-5/5.4 | 未公开 | 未公开 | No |

#### Aider 编程排行榜 (225 Exercism 编程题)

| 模型 | 得分 | 成本 |
|------|------|------|
| **GPT-5 (High)** | **88.0%** | $29.08 |
| GPT-5 (Medium) | 86.7% | $17.69 |
| o3-pro (High) | 84.9% | $146.00 |
| Gemini 2.5 Pro | 83.1% | - |
| GPT-5 (Low) | 81.3% | $10.37 |
| Claude Opus 4 (32K) | 72.0% | $65.75 |

#### 成本效益对比

| 模型 | 输入 ($/1M tokens) | 输出 ($/1M tokens) | SWE-bench | 性价比定位 |
|------|-------------------|-------------------|-----------|-----------|
| MiniMax M2.5 Lightning | **$0.30** | **$2.40** | 80.2% | 极致性价比 |
| Kimi K2.5 | $0.60 | - | 76.8% | 高性价比 |
| Claude Opus 4.6 | $5.00 | $25.00 | 71.7~81.4% | 旗舰级 |
| GPT-5 | ~$10.00 | ~$30.00 | 未公开 | 旗舰级 |
| GLM-5 | 订阅制 $10/月起 | - | 77.8% | 开源可私部 |

> **关键发现**: 开源 MoE 模型 (MiniMax M2.5, GLM-5, Kimi K2.5) 在编程基准测试上已接近甚至超过闭源旗舰模型，且成本低 1~2 个数量级。对于外包软件公司，这意味着可以在私有化部署的同时获得前沿级别的 AI 编程能力。

---

## 附录: 图表索引

| 图表 | 文件路径 | 说明 |
|------|---------|------|
| AI Coding 发展历程 | [diagrams/ai_coding_evolution.drawio](./diagrams/ai_coding_evolution.drawio) | 五阶段发展时间线 |
| AI Coding 技术全景图 | [diagrams/ai_coding_taxonomy.drawio](./diagrams/ai_coding_taxonomy.drawio) | 六大技术领域分类 |
| AI Coding Agent 核心架构 | [diagrams/ai_coding_agent_arch.drawio](./diagrams/ai_coding_agent_arch.drawio) | Agent 工作循环与组件 |
| AI Coding 与软件工程生命周期 | [diagrams/ai_coding_se_lifecycle.drawio](./diagrams/ai_coding_se_lifecycle.drawio) | 覆盖SE全阶段的AI工具 |

## 附录: LLM 定价参考 (2026年3月)

| 模型 | 输入价格 ($/1M tokens) | 输出价格 ($/1M tokens) | 备注 |
|------|----------------------|----------------------|------|
| Claude Opus 4.6 | $5 | $25 | 比 Opus 4.0 降价 67% |
| Claude Sonnet 4.6 | $3 | $15 | 2026.02.17 发布 |
| GPT-5 | ~$10 | ~$30 | Aider 排行榜第一 |
| GLM-5 | 订阅制 $10/月起 | - | MIT 开源，可私部 |
| Kimi K2.5 | $0.60 | - | 1T MoE，开源 |
| MiniMax M2.5 | **$0.30** | **$2.40** | 极致性价比，SWE-bench 80.2% |
| DeepSeek R1 | $0.55 | $2.19 | 671B MoE |

> Agent 工作流需要多次迭代调用，成本控制是实际部署的关键考量。开源 MoE 模型的成本优势在 Agent 场景下尤为显著。
