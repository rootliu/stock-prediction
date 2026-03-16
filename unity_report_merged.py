#!/usr/bin/env python3
"""
Merged Unity 3D Research Report — Push to Feishu Document.

Combines two existing reports and adds extensive new section on
World Model AI (Google Genie, Seedance) impact on Unity.
"""
import json, requests, time, sys

APP_ID = "cli_a907a415f5389ced"
APP_SECRET = "yOgQQrK8LyQuGRKeq6UOFVYDUIpsp7yu"
DOC_ID = "GtT5de3f0oZMTWxGUc7cwHyHnhe"
BASE = "https://open.feishu.cn/open-apis"


def get_token():
    r = requests.post(
        f"{BASE}/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
    )
    return r.json()["tenant_access_token"]


def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def text_el(content, bold=False, link=None):
    el = {"text_run": {"content": content, "text_element_style": {}}}
    if bold:
        el["text_run"]["text_element_style"]["bold"] = True
    if link:
        el["text_run"]["text_element_style"]["link"] = {"url": link}
    return el


def heading(level, text):
    bt = {1: 3, 2: 4, 3: 5, 4: 6}[level]
    key = f"heading{level}"
    return {"block_type": bt, key: {"elements": [text_el(text)]}}


def para(*elements):
    return {"block_type": 2, "text": {"elements": list(elements)}}


def bullet(*elements):
    return {"block_type": 12, "bullet": {"elements": list(elements)}}


def ordered(*elements):
    return {"block_type": 13, "ordered": {"elements": list(elements)}}


def code_block(lang, code_text):
    lang_map = {"csharp": 14, "python": 15, "text": 1}
    return {
        "block_type": 14,
        "code": {
            "language": lang_map.get(lang, 1),
            "elements": [text_el(code_text)],
        },
    }


def divider():
    return {"block_type": 22, "divider": {}}


# ── Feishu API helpers ───────────────────────────────────────────────


def delete_all_blocks(token):
    """Delete all child blocks of the document root to start fresh."""
    url = f"{BASE}/docx/v1/documents/{DOC_ID}/blocks/{DOC_ID}/children"
    r = requests.get(url, headers=headers(token), params={"page_size": 500})
    data = r.json()
    items = data.get("data", {}).get("items", [])
    if not items:
        print("Document already empty.")
        return

    # Delete from last to first
    child_ids = [item["block_id"] for item in items]
    for bid in reversed(child_ids):
        del_url = f"{BASE}/docx/v1/documents/{DOC_ID}/blocks/{bid}"
        dr = requests.delete(del_url, headers=headers(token))
        if dr.status_code != 200:
            # batch delete might fail on some, that's OK
            pass
        time.sleep(0.1)
    print(f"Deleted {len(child_ids)} blocks.")


def add_blocks(token, blocks, parent_id=None):
    pid = parent_id or DOC_ID
    url = f"{BASE}/docx/v1/documents/{DOC_ID}/blocks/{pid}/children"
    for i in range(0, len(blocks), 50):
        batch = blocks[i : i + 50]
        r = requests.post(
            url, headers=headers(token), json={"children": batch, "index": -1}
        )
        if r.status_code != 200:
            print(f"Error at batch {i}: {r.status_code} {r.text[:300]}")
        else:
            print(f"  Wrote blocks {i}-{i+len(batch)-1} OK")
        time.sleep(0.3)


# ── Report Content ───────────────────────────────────────────────────


def build_report():
    blocks = []
    b = blocks.append

    # ═══════════════════════════════════════════════════════════════════
    # PART 1 — OVERVIEW & HISTORY  (merged from both docs, Doc1 detail)
    # ═══════════════════════════════════════════════════════════════════

    b(heading(1, "第一章 起源与发展"))

    b(heading(2, "1.1 创始故事（2004-2005）"))
    b(
        para(
            text_el(
                "Unity Technologies 的前身 Over the Edge Entertainment 于 2004 年在丹麦哥本哈根成立，由三位联合创始人创建："
            )
        )
    )
    for name in [
        "David Helgason（CEO）",
        "Nicholas Francis（首席创意官）",
        "Joachim Ante（CTO）",
    ]:
        b(bullet(text_el(name)))
    b(
        para(
            text_el(
                "三人最初开发了一款游戏 GooBall（2005），但商业上失败。然而他们意识到为开发这款游戏而构建的工具本身更有价值，遂将公司方向转向游戏引擎开发。"
            )
        )
    )
    b(
        para(
            text_el("2005年6月，Unity 1.0 在 Apple WWDC 大会上首次亮相。最初是 Mac OS X 专用引擎，核心理念是"),
            text_el("\"让游戏开发民主化\"（Democratize Game Development）", bold=True),
            text_el("。2006年获 Apple Design Awards 亚军，2007年公司更名为 Unity Technologies。"),
        )
    )

    b(heading(2, "1.2 移动浪潮与崛起（2007-2012）"))
    b(
        para(
            text_el(
                "Unity 的第一次重大机遇来自 iPhone。2007年 iPhone 发布时，整个游戏行业聚焦在主机平台，Unity 是最早全面支持 iPhone 的引擎之一。"
            )
        )
    )
    for item in [
        "Unity 2.0（2007）：DirectX 支持、地形引擎、实时阴影、网络层",
        "Unity 2.5（2009）：Windows 编辑器支持",
        "Unity 3.0（2010）：Android 支持、Beast 光照贴图、延迟渲染",
        "Unity 4.0（2012）：DirectX 11、Mecanim 动画系统",
    ]:
        b(bullet(text_el(item)))
    b(
        para(
            text_el(
                "2012年 Game Developer 杂志调查显示，约 53% 的移动游戏开发者使用 Unity，此时已拥有超过 130 万注册开发者。"
            )
        )
    )

    b(heading(2, "1.3 全平台扩张（2013-2019）"))
    for item in [
        "2014：收购 Applifier（→ Unity Ads）、Playnomics（→ Unity Analytics），John Riccitiello（前 EA CEO）出任 CEO",
        "2015 Unity 5.0：WebGL 支持、PBR 渲染、免费 Personal 版（含完整引擎功能）",
        "2016：Pokémon Go 使用 Unity 开发并全球爆红，直接推动估值飙升",
        "2017：年度发布制取代序列版本号，引入 Timeline、Cinemachine、SRP",
        "2018：SRP 正式发布、Shader Graph、ECS/DOTS 预览、Unity Hub",
        "2019：收购 Vivox（$4880 万），年收入 $1.632 亿，自创立以来一直未盈利",
    ]:
        b(bullet(text_el(item)))

    b(heading(2, "1.4 上市与激进并购（2020-2022）"))
    for item in [
        "2020年9月17日：纽交所 IPO（NYSE: U），募资 $13.7 亿，月活开发者 150 万",
        "2021年11月：以 $16.3 亿收购 Weta Digital（彼得·杰克逊视效公司），同月股价达历史最高点",
        "2022年7月：以 $44 亿（全股票）收购 ironSource（广告变现平台）",
        "2022年8月：AppLovin 出价 $175.4 亿收购 Unity，被董事会拒绝",
    ]:
        b(bullet(text_el(item)))

    b(heading(2, "1.5 危机与重建（2023-2026）"))
    b(heading(3, "Runtime Fee 风波"))
    b(
        para(
            text_el(
                "2023年9月12日，Unity 宣布引入 Runtime Fee（运行时费用），按游戏安装量收费（$0.01-$0.20/次），引发行业地震："
            )
        )
    )
    for item in [
        "独立开发者强烈反对，Among Us 开发商 Innersloth、Slay the Spire 开发商 Mega Crit 等宣布弃用",
        "Unity 美国办公室因死亡威胁而临时关闭",
        "Gameindustry.biz 称此举为「自燃」（self-combustion）",
        "股价一年内暴跌 60%，Global Game Jam 中 Unity 使用率从 61% 暴跌至 36%",
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "领导层更迭"))
    for item in [
        "2023年10月：Riccitiello 辞职",
        "2024年1月：裁员 1,800 人（25%）",
        "2024年5月：Matthew Bromberg 出任永久 CEO",
        "2024年9月：Bromberg 宣布彻底取消 Runtime Fee，改为年度涨价",
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "Unity 6 与 Unity Studio"))
    b(
        para(
            text_el(
                "2024年10月17日发布 Unity 6，回归数字版本号。2025年推出 Unity Studio（浏览器无代码 3D 编辑器），面向设计师和非技术角色。"
            )
        )
    )

    b(divider())

    # ═══════════════════════════════════════════════════════════════════
    # PART 2 — MARKET & COMPETITION
    # ═══════════════════════════════════════════════════════════════════

    b(heading(1, "第二章 市场现状与竞争格局"))

    b(heading(2, "2.1 Unity 市场地位（2025-2026）"))
    for item in [
        "全球移动游戏市场占约 50% 份额（但独立社区有所下滑）",
        "AR/VR 内容占 60%，新兴 AR 平台占 90%",
        "月活用户 20 亿+，月下载量 30 亿+",
        "支持 25+ 平台",
        "收入结构：Operate Solutions（广告/IAP）约 54%，Create Solutions（引擎订阅）约 31%",
    ]:
        b(bullet(text_el(item)))

    b(heading(2, "2.2 主要竞争对手"))

    b(heading(3, "Unreal Engine 5（Epic Games）"))
    for item in [
        "AAA 级画质（Nanite、Lumen、MetaHuman），C++/Blueprints",
        "收入超 $100 万后收取 5% 版税，Epic Store 独占免版税",
        "强项：电影级渲染、大型开放世界、虚拟制片（曼达洛人等）",
        "弱项：学习曲线陡峭、移动端优化不如 Unity",
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "Godot Engine"))
    for item in [
        "MIT 开源，完全免费，GDScript/C#/C++",
        "Runtime Fee 事件后用户暴增，成为独立开发者主要替代",
        "3D 能力持续增强但生态仍不成熟",
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "其他竞争者"))
    for item in [
        "CryEngine：画质强但社区小，边缘化",
        "Cocos Creator：中国微信小游戏市场份额极高",
        "O3DE（前 Amazon Lumberyard）：开源但活跃度低",
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "竞争格局总结"))
    for item in [
        "AAA 游戏：Unreal 主导",
        "移动 / 中小型 3D 游戏：Unity 主导（份额下降中）",
        "独立 / Jam 游戏：Godot 快速崛起",
        "AR/VR：Unity 仍然主导",
        "中国市场：Unity + Cocos 双头格局",
    ]:
        b(bullet(text_el(item)))

    b(divider())

    # ═══════════════════════════════════════════════════════════════════
    # PART 3 — TECHNICAL DEEP DIVE
    # ═══════════════════════════════════════════════════════════════════

    b(heading(1, "第三章 技术架构深度解析"))

    b(heading(2, "3.1 引擎核心架构"))
    b(
        para(
            text_el(
                "Unity 引擎采用 C++ 编写核心运行时，上层通过 C#（Mono/IL2CPP）提供脚本 API。架构分层："
            )
        )
    )

    b(para(text_el("底层（C++ Runtime）", bold=True)))
    for item in [
        "渲染引擎（Rendering Engine）",
        "物理引擎（Nvidia PhysX / Box2D）",
        "音频引擎（FMOD 整合）",
        "内存管理与垃圾回收",
        "平台抽象层（Platform Abstraction Layer）",
    ]:
        b(bullet(text_el(item)))

    b(para(text_el("中间层（Core Systems）", bold=True)))
    for item in [
        "ECS：传统 GameObject + Component；DOTS 引入纯 ECS",
        "Scripting Runtime：Mono（开发期）/ IL2CPP（发布期，C# → C++ → Native）",
        "Asset Pipeline v2：并行导入、ScriptedImporter",
        "Scene Management：场景图、层级管理、序列化",
    ]:
        b(bullet(text_el(item)))

    b(para(text_el("上层（Editor & Tools）", bold=True)))
    for item in [
        "Unity Editor（IMGUI / UI Toolkit）",
        "Unity Hub（版本/项目/许可证管理）",
        "Package Manager（UPM）",
        "Profiler、Memory Profiler、Frame Debugger",
    ]:
        b(bullet(text_el(item)))

    b(heading(2, "3.2 渲染管线"))
    for item in [
        "Built-in Render Pipeline（Legacy）：Forward/Deferred，功能完整但不可定制",
        "URP（Universal Render Pipeline）：面向移动/VR/全平台，SRP Batcher 优化 Draw Call",
        "HDRP（High Definition Render Pipeline）：面向高端 PC/主机，PBR、体积云/雾、DXR 光追、SSGI",
    ]:
        b(bullet(text_el(item)))
    b(
        para(
            text_el(
                "三条管线互不兼容，开发者必须在项目初期选择，切换成本极高——这是 Unity 的一个历史包袱。"
            )
        )
    )

    b(heading(2, "3.3 DOTS（Data-Oriented Technology Stack）"))
    for item in [
        "ECS：Entity + Component（纯数据）+ System（逻辑），Cache-friendly 内存布局",
        "C# Job System：多线程任务调度",
        "Burst Compiler：C# → LLVM → 高度优化原生代码，性能接近手写 C++",
        "Unity Collections：NativeArray/NativeList，不走 GC",
    ]:
        b(bullet(text_el(item)))
    b(
        para(
            text_el(
                "DOTS 可在同一场景内管理数十万实体，但学习曲线陡峭，API 变动频繁，至今未被社区广泛采用。"
            )
        )
    )

    b(heading(2, "3.4 脚本与 IL2CPP"))
    b(
        para(
            text_el(
                "Unity 使用 C# 作为唯一脚本语言。核心生命周期：Awake() → OnEnable() → Start() → Update() → FixedUpdate() → LateUpdate() → OnDisable() → OnDestroy()。"
            )
        )
    )
    b(
        para(
            text_el("IL2CPP 工作原理：", bold=True),
            text_el(
                "C# Source → Mono Compiler → IL → IL2CPP → C++ Source → Platform Native Compiler → Machine Code。优势：更好性能、代码混淆、支持不允许 JIT 的平台（iOS）。"
            ),
        )
    )

    b(heading(2, "3.5 跨平台部署"))
    b(para(text_el("Unity 支持 25+ 平台一次开发多端部署：")))
    for item in [
        "桌面：Windows、macOS、Linux",
        "移动：iOS、Android",
        "主机：PS4/PS5、Xbox One/Series X|S、Nintendo Switch",
        "Web：WebGL（IL2CPP → WASM），WebGPU 预览中",
        "XR：Meta Quest 2/3/Pro、Apple Vision Pro（PolySpatial）、HoloLens 2、PSVR2",
        "嵌入式：Embedded Linux、QNX（汽车座舱）",
    ]:
        b(bullet(text_el(item)))

    b(divider())

    # ═══════════════════════════════════════════════════════════════════
    # PART 4 — GAME & INDUSTRY APPLICATIONS
    # ═══════════════════════════════════════════════════════════════════

    b(heading(1, "第四章 游戏与行业应用"))

    b(heading(2, "4.1 知名 Unity 游戏"))
    for item in [
        "Pokémon Go（Niantic, 2016）— 全球现象级 AR 游戏",
        "Genshin Impact（miHoYo/HoYoverse, 2020）— 开放世界 RPG（深度定制 Unity）",
        "Call of Duty: Mobile（Activision, 2019）— 3A 级移动射击",
        "Beat Saber（Beat Games, 2018）— VR 音乐节奏游戏标杆",
        "Cuphead、Hollow Knight、Among Us、Hearthstone、Subway Surfers 等",
    ]:
        b(bullet(text_el(item)))

    b(heading(2, "4.2 游戏之外的行业应用"))
    for item in [
        "影视/VFX：Weta Digital（$16.3 亿收购）、Disney Baymax Dreams、虚拟制作 LED Volume",
        "汽车：HMI 座舱设计（BMW、Volvo、Hyundai）、Unity Forma 配置器、QNX 部署",
        "建筑/AEC：Unity Reflect 实时 BIM、AR/VR 建筑漫游、数字孪生",
        "仿真训练：军事模拟、医疗手术训练、自动驾驶仿真（ML-Agents + Perception）",
        "机器学习：Google DeepMind 使用 Unity 训练 AI、合成数据生成",
    ]:
        b(bullet(text_el(item)))

    b(divider())

    # ═══════════════════════════════════════════════════════════════════
    # PART 5 — DEVELOPER ECOSYSTEM
    # ═══════════════════════════════════════════════════════════════════

    b(heading(1, "第五章 开发者社区与生态"))
    for item in [
        "Asset Store（2010 年上线）：6 万+ 资产，开发者 70% / Unity 30% 分成",
        "社区规模：2020 年 150 万月活创作者；Reddit r/Unity3D 50 万+；官方 Discord",
        "Unity Learn：免费结构化学习平台",
        "认证：Unity Certified User / Programmer / Artist / Expert",
        "大会：Unite 年度全球开发者大会",
        "开源：ML-Agents、XR Interaction Toolkit 等开源；引擎本身不开源",
    ]:
        b(bullet(text_el(item)))

    b(divider())

    # ═══════════════════════════════════════════════════════════════════
    # PART 6 — BUSINESS MODEL
    # ═══════════════════════════════════════════════════════════════════

    b(heading(1, "第六章 商业模式"))

    b(heading(2, "6.1 订阅许可"))
    for item in [
        "Personal（免费）：年收入 <$20 万",
        "Pro（~$2,040/年/席位）：年收入 >$20 万",
        "Enterprise / Industry：大型组织定制、非游戏行业",
    ]:
        b(bullet(text_el(item)))

    b(heading(2, "6.2 广告与运营服务（Operate Solutions）"))
    b(
        para(
            text_el(
                "这是 Unity 最赚钱的业务（占收入 54%）：Unity Ads、ironSource（$44 亿收购）、Unity IAP、Vivox 语音。"
            )
        )
    )

    b(heading(2, "6.3 其他收入"))
    for item in [
        "Asset Store 分成（30%）",
        "Unity Gaming Services（UGS）：多人网络、云存储、分析",
        "AI 产品：Unity Muse、Sentis、Unity AI（Unity Points 计费）",
        "行业解决方案：汽车 HMI、建筑可视化、数字孪生",
    ]:
        b(bullet(text_el(item)))

    b(divider())

    # ═══════════════════════════════════════════════════════════════════
    # PART 7 — CHINA
    # ═══════════════════════════════════════════════════════════════════

    b(heading(1, "第七章 中国区情况"))
    for item in [
        "Unity China（合资公司）：2019-2020 年成立，2022 年融资 $10 亿（阿里巴巴、中国移动、OPPO），估值 $20 亿",
        "团结引擎（Tuanjie Engine）：2023年8月发布，基于 Unity 2022 LTS，支持微信小游戏、OpenHarmony、AliOS",
        "标杆产品：原神（miHoYo）、崩坏3、崩坏：星穹铁道、明日方舟、碧蓝航线、万国觉醒",
        "竞争：Cocos Creator 在微信小游戏领域份额极高；Unreal 在高端中国游戏中份额上升",
        "社区：Unity 中国官网完整中文支持、Unite 中国大会、B站/知乎活跃教学社区",
    ]:
        b(bullet(text_el(item)))

    b(divider())

    # ═══════════════════════════════════════════════════════════════════
    # PART 8 — AI IMPACT (GREATLY EXPANDED — Core new content)
    # ═══════════════════════════════════════════════════════════════════

    b(heading(1, "第八章 AI 对 Unity 及 3D 行业的冲击与展望"))
    b(
        para(
            text_el(
                "这是本报告的核心扩展章节。2024-2025 年，以 Google Genie 为代表的 World Model AI 的崛起，正在从根本上重新定义「3D 内容创建」的含义，对 Unity 等传统游戏引擎构成了前所未有的存在性挑战。",
                bold=True,
            )
        )
    )

    # ── 8.1 Unity 官方 AI 工具 ──

    b(heading(2, "8.1 Unity 官方 AI 工具"))
    for item in [
        "Unity AI（Beta）：集成在 Editor 中的 AI 助手，基于第三方 Generative AI 模型，支持自动化任务、资产生成、上下文辅助开发。使用 Unity Points 计费。",
        "Unity Muse：Unity 自研第一方模型，提供纹理生成、Sprite 生成、Chat-based 代码辅助",
        "Unity Sentis：端侧 ML 推理引擎，支持 ONNX 模型在 Unity Runtime 中运行（NPC 行为、风格迁移、语音识别等）",
        "ML-Agents Toolkit：强化学习训练框架，训练游戏 AI、自动化测试、仿真",
    ]:
        b(bullet(text_el(item)))
    b(
        para(
            text_el(
                "然而，Unity 的 AI 工具主要定位为「辅助现有工作流」的增量式改进，而非颠覆性创新。真正的颠覆来自外部——尤其是 World Model AI。"
            )
        )
    )

    # ── 8.2 Google Genie — World Model AI ──

    b(heading(2, "8.2 Google Genie：World Model AI 的崛起"))
    b(
        para(
            text_el(
                "Google DeepMind 的 Genie 系列是 World Model AI 领域最具代表性的突破。它代表了一种全新范式：不再通过传统引擎手工构建 3D 世界，而是通过 AI 模型直接从文本/图像生成可交互的虚拟环境。"
            )
        )
    )

    b(heading(3, "Genie 1（2024年2月）"))
    for item in [
        "Google DeepMind 发布论文「Genie: Generative Interactive Environments」",
        "首个从单张图像生成可交互 2D 环境的基础世界模型（Foundation World Model）",
        "110 亿参数（11B），在 20 万小时互联网游戏视频上无监督训练",
        "核心架构：Video Tokenizer + Latent Action Model + Dynamics Model",
        "可从文本描述、草图、甚至真实照片生成可玩的 2D 平台游戏环境",
        "局限：分辨率低（160×90 像素）、帧率 1 FPS、仅支持 2D",
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "Genie 2（2024年12月）"))
    for item in [
        "从 2D 跃迁到 3D：从单张图像生成可交互的 3D 环境",
        "支持第一人称和第三人称视角",
        "生成时长从几秒扩展到数十秒的一致性交互体验",
        "物理模拟改进：物体交互、重力、碰撞等更真实",
        "用于训练通用 AI Agent（如 Google 的 SIMA 项目）",
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "Genie 3（2025年）"))
    for item in [
        "被描述为「首个实时、可交互的光照级世界模型」",
        "从简单文本描述生成 720p 照片级真实感环境",
        "实时运行：20-24 帧/秒，流畅可探索",
        "环境一致性：回到之前访问过的位置时记住细节，记忆持续约 1 分钟",
        "自回归架构：逐帧生成，基于世界描述和用户动作",
        "应用场景扩展：教育（探索古罗马）、自动驾驶训练、AI Agent 研究",
        "当前局限：Agent 动作空间有限、多 Agent 交互困难、文本渲染问题、交互时长限几分钟",
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "Genie 对 Unity 的冲击分析"))
    b(
        para(
            text_el(
                "Genie 系列的核心冲击在于：它从根本上质疑了「为什么我们需要一个复杂的游戏引擎来构建 3D 世界？」这一前提。",
                bold=True,
            )
        )
    )
    for item in [
        "范式转变：传统引擎工作流（建模→材质→光照→物理→脚本→测试）可能被「文本→世界」的一步到位所替代",
        "原型阶段颠覆：即使 Genie 短期内无法替代完整游戏开发，它已经可以极大加速概念验证和原型制作",
        "Unity 股价影响：Genie 2 发布后（2024年12月），Unity 股价承压。市场将 World Model AI 视为对传统引擎商业模式的长期威胁",
        "人才争夺：World Model AI 领域的顶尖研究人才正在被 Google、Meta、字节跳动等公司高薪招募，Unity 在 AI 研究人才上处于劣势",
        "长期威胁：如果 World Model 成熟到可以生成持续数小时的一致性交互体验，Unity 的核心价值主张——跨平台 3D 内容创建工具——将面临存在性危机",
    ]:
        b(bullet(text_el(item)))

    # ── 8.3 Seedance 与字节跳动的 World Model 布局 ──

    b(heading(2, "8.3 Seedance 与字节跳动的 World Model 布局"))
    b(
        para(
            text_el(
                "字节跳动（ByteDance）通过其 AI 研究实验室推出了 Seedance（种子舞蹈）系列模型，是中国在 World Model / 视频生成领域最具代表性的工作："
            )
        )
    )

    b(heading(3, "Seedance 技术特点"))
    for item in [
        "高质量视频生成：从文本/图像生成高分辨率、长时长视频，物理一致性强",
        "运动控制：精确的角色运动控制、相机运动控制、物体交互",
        "世界模型潜力：视频生成模型本质上在学习世界的物理规律（重力、碰撞、光照、材质），距离「可交互的世界模型」仅一步之遥",
        "与 Genie 的互补：Genie 侧重交互性（可控 Agent），Seedance 侧重视觉保真度（电影级画质）",
        "背后技术：基于 Diffusion Transformer（DiT）架构，大规模视频数据训练",
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "Seedance 对 Unity 的影响"))
    for item in [
        "影视制作替代：Unity 的一个重要非游戏场景是虚拟制作（Virtual Production），Seedance 级别的视频生成可能部分替代实时渲染引擎",
        "中国市场冲击：字节跳动在中国市场的影响力远超 Unity China，如果 Seedance 发展为完整的 World Model 平台，对团结引擎构成直接竞争",
        "内容生成加速：结合 Seedance 的视频生成 + 3D 重建（如 NeRF/3D Gaussian Splatting），可以绕过传统建模工作流",
        "广告行业冲击：Unity 超过 54% 的收入来自广告平台（ironSource），AI 视频生成可能改变广告素材制作方式，间接影响 Unity 的广告业务",
    ]:
        b(bullet(text_el(item)))

    # ── 8.4 更广泛的 World Model AI 生态 ──

    b(heading(2, "8.4 更广泛的 World Model AI 生态"))
    b(
        para(
            text_el(
                "除 Google Genie 和字节跳动 Seedance 外，多家公司正在推进 World Model AI："
            )
        )
    )
    for item in [
        "OpenAI Sora：文本到视频生成，展示了强大的物理世界理解能力，被 OpenAI 定义为「世界模拟器」",
        "Meta / FAIR：Yann LeCun 提出的 JEPA（Joint Embedding Predictive Architecture）是 World Model 的理论基础，Meta 在开源 World Model 研究上投入巨大",
        "Runway Gen-3 / Luma Dream Machine：商业化视频生成工具，已被影视和广告行业采用",
        "NVIDIA Cosmos：NVIDIA 2025年推出的 World Foundation Model 平台，专为物理 AI、机器人和自动驾驶设计",
        "Decart / Oasis：开源实时 AI 游戏引擎，可以从用户输入实时生成类 Minecraft 的 3D 体验",
        "World Labs（Fei-Fei Li）：斯坦福教授李飞飞创办的 World Model 创业公司，估值已达 $10 亿+",
    ]:
        b(bullet(text_el(item)))

    # ── 8.5 AI 对游戏引擎的存在性威胁 ──

    b(heading(2, "8.5 AI 对传统游戏引擎的存在性威胁分析"))

    b(heading(3, "短期（2025-2027）：增量式影响"))
    for item in [
        "AI 辅助开发成为标配：代码补全（Copilot/Claude）、AI 纹理/3D 模型生成、自动化测试",
        "Unity/Unreal 将 AI 集成为引擎功能——这一阶段 AI 是「助手」而非「替代者」",
        "开发周期缩短 30-50%：1-3 人独立团队可完成过去 10+ 人的工作",
        "AI NPC：LLM 驱动的动态对话（Inworld AI、NVIDIA ACE）、自适应难度系统",
        "World Model 用于原型和概念验证，但不能替代完整的游戏开发管线",
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "中期（2027-2030）：范式转变开始"))
    for item in [
        "World Model 成熟：可生成持续 10-30 分钟的一致性交互体验",
        "「AI-Native 游戏引擎」出现：从头为 AI 工作流设计，而非在传统引擎上「贴」AI 功能",
        "Unity/Unreal 的角色转变：从「创建工具」变为「渲染/部署/优化后端」",
        "Procedural Generation 与 World Model 融合：关卡、剧情、NPC、音乐全部 AI 实时生成",
        "3D 重建技术（NeRF、3D Gaussian Splatting）与视频生成结合，绕过传统建模管线",
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "长期（2030+）：行业重构"))
    for item in [
        "从「游戏引擎」到「实时 3D 操作系统」：Unity/Unreal 需要重新定义自身",
        "「意图驱动」取代「手工编码」：开发者描述意图，AI 生成世界",
        "个性化内容：每个玩家体验完全独特的 AI 生成游戏世界",
        "引擎市场集中：小型引擎（CryEngine、O3DE）被淘汰，只有 Unity、Unreal 和新兴 AI-Native 引擎生存",
        "Spatial Computing（Apple Vision Pro、Meta Quest）+ World Model = 3D 互联网入口",
    ]:
        b(bullet(text_el(item)))

    # ── 8.6 Unity 的 AI 应对策略评估 ──

    b(heading(2, "8.6 Unity 的 AI 应对策略评估"))

    b(para(text_el("机遇：", bold=True)))
    for item in [
        "AI 工具（Muse、Sentis）可能是重建开发者信任的关键",
        "Unity Studio（无代码浏览器编辑器）配合 AI 可大幅扩大用户基数",
        "Weta Digital 的技术资产在 AI 内容生成时代更有价值（3D 数据集、工具链）",
        "非游戏行业（汽车、建筑、数字孪生）对传统引擎的需求短期内不会被 World Model 替代",
        "Unity 在移动端部署和优化方面的深厚积累是 AI-Native 引擎短期无法替代的",
        "与 World Model 提供商合作（如集成 Genie API 作为世界生成后端）可以转危为机",
    ]:
        b(bullet(text_el(item)))

    b(para(text_el("风险：", bold=True)))
    for item in [
        "Runtime Fee 事件的信任危机尚未完全恢复，开发者忠诚度降低",
        "Godot 在独立开发者中持续蚕食",
        "AI 研究人才争夺中处于劣势（对比 Google、Meta、NVIDIA）",
        "股价低迷限制了并购和研发投入能力",
        "广告业务（54% 收入）可能被 AI 视频生成工具改变",
        "如果 World Model 技术快速成熟，Unity 的核心引擎订阅业务将面临缩水",
    ]:
        b(bullet(text_el(item)))

    b(para(text_el("建议关注的关键指标：", bold=True)))
    for item in [
        "Unity 是否会收购或深度合作 World Model AI 公司",
        "Unity Sentis 在端侧 AI 推理市场的采用率",
        "Unity 6 的月活开发者增长率 vs Godot 增长率",
        "Google Genie / NVIDIA Cosmos 的商业化进展速度",
        "Unity 在非游戏行业收入占比的变化趋势",
    ]:
        b(bullet(text_el(item)))

    # ── 8.7 AI 在当前游戏开发中的具体应用 ──

    b(heading(2, "8.7 AI 在当前游戏开发中的具体应用"))
    for item in [
        "程序化内容生成（PCG）：AI 驱动的关卡设计、地形生成、任务系统（WaveFunctionCollapse、GAN、Diffusion Model）",
        "AI NPC 行为：大语言模型驱动的动态对话、自适应难度、情感反应系统（Inworld AI、Convai、NVIDIA ACE）",
        "AI 资产生成：Stability AI / Midjourney 生成纹理，3D 模型生成（Meshy、Tripo3D、Point-E、Shap-E）",
        "AI 动画：Motion Diffusion Model、文本到动画、动作捕捉替代方案",
        "AI 辅助编程：GitHub Copilot、Claude、Cursor 大幅提升 Unity C# 开发效率",
        "AI 测试：自动化 QA、AI 驱动的游戏平衡测试、玩家行为模拟",
    ]:
        b(bullet(text_el(item)))

    b(divider())

    # ═══════════════════════════════════════════════════════════════════
    # PART 9 — CODE EXAMPLES
    # ═══════════════════════════════════════════════════════════════════

    b(heading(1, "第九章 开发项目示例"))

    # ── Example 1: FPS ──
    b(heading(2, "9.1 FPS 射击游戏（Unity 6 + URP）"))

    b(heading(3, "项目结构"))
    b(
        code_block(
            "text",
            """MyFPSGame/
├── Assets/
│   ├── Scripts/
│   │   ├── Player/
│   │   │   ├── PlayerController.cs
│   │   │   ├── PlayerHealth.cs
│   │   │   └── WeaponSystem.cs
│   │   ├── Enemy/
│   │   │   ├── EnemyAI.cs
│   │   │   └── EnemySpawner.cs
│   │   ├── UI/
│   │   │   └── HUDManager.cs
│   │   └── GameManager.cs
│   ├── Prefabs/
│   ├── Scenes/
│   ├── Materials/
│   └── Audio/
├── Packages/manifest.json
└── ProjectSettings/""",
        )
    )

    b(heading(3, "PlayerController.cs"))
    b(
        code_block(
            "csharp",
            """using UnityEngine;

[RequireComponent(typeof(CharacterController))]
public class PlayerController : MonoBehaviour
{
    [Header("Movement")]
    [SerializeField] private float moveSpeed = 6f;
    [SerializeField] private float jumpForce = 8f;
    [SerializeField] private float gravity = 20f;

    [Header("Look")]
    [SerializeField] private float mouseSensitivity = 2f;
    [SerializeField] private Transform cameraTransform;

    private CharacterController controller;
    private Vector3 velocity;
    private float xRotation = 0f;

    void Start()
    {
        controller = GetComponent<CharacterController>();
        Cursor.lockState = CursorLockMode.Locked;
    }

    void Update()
    {
        // Look
        float mouseX = Input.GetAxis("Mouse X") * mouseSensitivity;
        float mouseY = Input.GetAxis("Mouse Y") * mouseSensitivity;
        xRotation -= mouseY;
        xRotation = Mathf.Clamp(xRotation, -90f, 90f);
        cameraTransform.localRotation = Quaternion.Euler(xRotation, 0f, 0f);
        transform.Rotate(Vector3.up * mouseX);

        // Move
        if (controller.isGrounded)
        {
            float moveX = Input.GetAxis("Horizontal");
            float moveZ = Input.GetAxis("Vertical");
            velocity = transform.right * moveX + transform.forward * moveZ;
            velocity *= moveSpeed;
            if (Input.GetButtonDown("Jump"))
                velocity.y = jumpForce;
        }
        velocity.y -= gravity * Time.deltaTime;
        controller.Move(velocity * Time.deltaTime);
    }
}""",
        )
    )

    b(heading(3, "WeaponSystem.cs"))
    b(
        code_block(
            "csharp",
            """using UnityEngine;

public class WeaponSystem : MonoBehaviour
{
    [SerializeField] private GameObject bulletPrefab;
    [SerializeField] private Transform firePoint;
    [SerializeField] private float fireRate = 0.15f;
    [SerializeField] private float bulletSpeed = 50f;
    [SerializeField] private int maxAmmo = 30;
    [SerializeField] private float reloadTime = 1.5f;

    private int currentAmmo;
    private float nextFireTime;
    private bool isReloading;

    void Start() => currentAmmo = maxAmmo;

    void Update()
    {
        if (isReloading) return;
        if (currentAmmo <= 0 || Input.GetKeyDown(KeyCode.R))
        { StartCoroutine(Reload()); return; }
        if (Input.GetButton("Fire1") && Time.time >= nextFireTime)
        {
            nextFireTime = Time.time + fireRate;
            currentAmmo--;
            GameObject bullet = Instantiate(bulletPrefab, firePoint.position, firePoint.rotation);
            bullet.GetComponent<Rigidbody>().velocity = firePoint.forward * bulletSpeed;
            Destroy(bullet, 3f);
        }
    }

    System.Collections.IEnumerator Reload()
    {
        isReloading = true;
        yield return new WaitForSeconds(reloadTime);
        currentAmmo = maxAmmo;
        isReloading = false;
    }
}""",
        )
    )

    # ── Example 2: Coin Collector ──
    b(heading(2, "9.2 Coin Collector 移动游戏"))
    b(para(text_el("一个完整的 3D 移动游戏示例 — 玩家在场景中移动收集金币，包含计分 UI。")))

    b(heading(3, "PlayerController.cs（New Input System）"))
    b(
        code_block(
            "csharp",
            """using UnityEngine;
using UnityEngine.InputSystem;

[RequireComponent(typeof(Rigidbody))]
public class PlayerController : MonoBehaviour
{
    [SerializeField] private float moveSpeed = 6f;
    [SerializeField] private float rotationSpeed = 720f;
    private Rigidbody _rb;
    private Vector2 _moveInput;

    private void Awake() {
        _rb = GetComponent<Rigidbody>();
        _rb.constraints = RigidbodyConstraints.FreezeRotation;
    }

    public void OnMove(InputAction.CallbackContext ctx) {
        _moveInput = ctx.ReadValue<Vector2>();
    }

    private void FixedUpdate() {
        var movement = new Vector3(_moveInput.x, 0f, _moveInput.y);
        if (movement.sqrMagnitude > 0.01f) {
            _rb.MovePosition(_rb.position + movement.normalized * moveSpeed * Time.fixedDeltaTime);
            _rb.rotation = Quaternion.RotateTowards(
                _rb.rotation, Quaternion.LookRotation(movement), rotationSpeed * Time.fixedDeltaTime);
        }
    }
}""",
        )
    )

    b(heading(3, "ScoreManager.cs（Singleton）"))
    b(
        code_block(
            "csharp",
            """using UnityEngine;
using System;

public class ScoreManager : MonoBehaviour
{
    public static ScoreManager Instance { get; private set; }
    public event Action<int> OnScoreChanged;
    public int CurrentScore { get; private set; }

    private void Awake() {
        if (Instance != null && Instance != this) { Destroy(gameObject); return; }
        Instance = this;
        DontDestroyOnLoad(gameObject);
    }

    public void AddScore(int amount) {
        CurrentScore += amount;
        OnScoreChanged?.Invoke(CurrentScore);
    }
}""",
        )
    )

    b(heading(3, "构建与部署"))
    for item in [
        "安装 Unity Hub → Unity 6 LTS → 选择 URP 模板",
        "File → Build Settings → 选择目标平台",
        "PC 生成 .exe；Android 生成 .apk/.aab；iOS 生成 Xcode Project；WebGL 生成 HTML5 + WASM",
        "优化：Profiler → Quality Settings → 纹理压缩 → 对象池化",
    ]:
        b(ordered(text_el(item)))

    b(divider())

    # ═══════════════════════════════════════════════════════════════════
    # PART 10 — REFERENCES
    # ═══════════════════════════════════════════════════════════════════

    b(heading(1, "第十章 参考信源"))
    b(para(text_el("以下全部为英文信源：", bold=True)))

    refs = [
        ("Wikipedia - Unity (game engine)", "https://en.wikipedia.org/wiki/Unity_(game_engine)"),
        ("Wikipedia - Unity Technologies", "https://en.wikipedia.org/wiki/Unity_Technologies"),
        ("Unity Official Website", "https://unity.com"),
        ("Unity Blog", "https://blog.unity.com"),
        ("Unity Documentation", "https://docs.unity3d.com"),
        ("Unity Learn", "https://learn.unity.com"),
        ("Unity AI Products", "https://unity.com/ai"),
        ("Runtime Fee Cancellation", "https://blog.unity.com/news/unity-is-canceling-the-runtime-fee"),
        ("Unity China / Tuanjie", "https://unity.cn"),
        ("Unity IPO / Financials (SEC)", "https://investors.unity.com"),
        ("Google DeepMind Genie", "https://deepmind.google/models/genie/"),
        ("Google DeepMind Genie 1 Paper (arXiv)", "https://arxiv.org/abs/2402.15391"),
        ("Google DeepMind Genie 2 Blog", "https://deepmind.google/discover/blog/genie-2-a-large-scale-foundation-world-model/"),
        ("NVIDIA Cosmos World Foundation Model", "https://developer.nvidia.com/cosmos"),
        ("OpenAI Sora", "https://openai.com/sora"),
        ("ByteDance Seedance / Seed Video", "https://seed-video-gen.github.io/"),
        ("World Labs (Fei-Fei Li)", "https://www.worldlabs.ai/"),
        ("Decart / Oasis (Open-source AI game engine)", "https://oasis-model.github.io/"),
        ("Ars Technica — Runtime Fee Analysis", "https://arstechnica.com"),
        ("Game Developer (GDC)", "https://www.gamedeveloper.com"),
        ("Gameindustry.biz — Unity Analysis", "https://www.gamesindustry.biz"),
        ("VentureBeat Gaming / AI", "https://venturebeat.com/games/"),
        ("Unreal Engine (Competitor)", "https://www.unrealengine.com"),
        ("Godot Engine (Competitor)", "https://godotengine.org"),
        ("Cocos Creator (Competitor)", "https://www.cocos.com"),
        ("Inworld AI (AI NPC)", "https://inworld.ai"),
        ("NVIDIA ACE (Avatar Cloud Engine)", "https://developer.nvidia.com/ace"),
    ]
    for i, (name, url) in enumerate(refs, 1):
        b(para(text_el(f"{i}. {name} — "), text_el(url, link=url)))

    b(divider())
    b(
        para(
            text_el("报告生成时间：2026-03-05 | 数据截止：2025 年初 | 建议核实最新财务数据于 "),
            text_el("investors.unity.com", link="https://investors.unity.com"),
        )
    )

    return blocks


# ── Main ─────────────────────────────────────────────────────────────


if __name__ == "__main__":
    print("Getting Feishu token...")
    token = get_token()
    print(f"Token: {token[:20]}...")

    print("\nClearing existing document content...")
    delete_all_blocks(token)

    print("\nBuilding merged report blocks...")
    blocks = build_report()
    print(f"Total blocks: {len(blocks)}")

    print("\nWriting to Feishu document...")
    add_blocks(token, blocks)

    doc_url = f"https://my.feishu.cn/docx/{DOC_ID}"
    print(f"\nDone! Document URL: {doc_url}")
