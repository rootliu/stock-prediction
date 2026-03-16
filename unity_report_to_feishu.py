#!/usr/bin/env python3
"""Push Unity 3D report to Feishu document via API."""
import json, requests, time

APP_ID = "cli_a907a415f5389ced"
APP_SECRET = "yOgQQrK8LyQuGRKeq6UOFVYDUIpsp7yu"
DOC_ID = "GtT5de3f0oZMTWxGUc7cwHyHnhe"
BASE = "https://open.feishu.cn/open-apis"

def get_token():
    r = requests.post(f"{BASE}/auth/v3/tenant_access_token/internal",
                      json={"app_id": APP_ID, "app_secret": APP_SECRET})
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
    return {"block_type": {1:3, 2:4, 3:5, 4:6}[level],
            f"heading{level}": {"elements": [text_el(text)]}}

def para(*elements):
    return {"block_type": 2, "text": {"elements": list(elements)}}

def bullet(*elements):
    return {"block_type": 12, "bullet": {"elements": list(elements)}}

def ordered(*elements):
    return {"block_type": 13, "ordered": {"elements": list(elements)}}

def code_block(lang, code_text):
    return {"block_type": 14, "code": {
        "language": 14 if lang == "csharp" else 1,
        "elements": [text_el(code_text)]}}

def divider():
    return {"block_type": 22, "divider": {}}

def add_blocks(token, blocks, parent_id=None):
    pid = parent_id or DOC_ID
    url = f"{BASE}/docx/v1/documents/{DOC_ID}/blocks/{pid}/children"
    # API limit: max 50 blocks per call
    for i in range(0, len(blocks), 50):
        batch = blocks[i:i+50]
        r = requests.post(url, headers=headers(token), json={"children": batch, "index": -1})
        if r.status_code != 200:
            print(f"Error at batch {i}: {r.status_code} {r.text[:300]}")
        else:
            print(f"Wrote blocks {i}-{i+len(batch)-1} OK")
        time.sleep(0.3)

def build_report():
    blocks = []
    b = blocks.append

    # ===== Part 1: Overview =====
    b(heading(1, "一、Unity 3D 概览"))
    b(heading(2, "1.1 起源与发展"))
    b(para(text_el("Unity 由 "), text_el("David Helgason、Joachim Ante、Nicholas Francis", bold=True),
           text_el(" 于 2004 年在丹麦哥本哈根创立（原名 Over the Edge Entertainment，2007 年更名 Unity Technologies）。")))
    b(para(text_el("2005 年 WWDC 上发布 Unity 1.0（仅支持 Mac OS X），此后逐步扩展为全平台 3D 引擎。")))

    b(heading(3, "关键里程碑"))
    for item in [
        "2005 — Unity 1.0 发布（Mac OS X 专属）",
        "2010 — Unity 3.0：Deferred Rendering、Android 支持",
        "2012 — Unity 4.0：DirectX 11、Mecanim 动画系统",
        "2015 — Unity 5.0：PBR 渲染、免费 Personal 版（含完整引擎功能）",
        "2017 — 改用年份命名，引入 Timeline、Cinemachine、Scriptable Render Pipeline",
        "2018 — SRP 正式发布、Shader Graph、ECS/DOTS 预览",
        "2020 — IPO 上市（NYSE: U），首日估值 ~137 亿美元",
        "2021 — 收购 Weta Digital 工具部门（$16.25 亿）、Parsec（$3.2 亿）",
        "2022 — 与 IronSource 合并（$44 亿），ECS 1.0 发布",
        "2023 — Runtime Fee 风波，CEO Riccitiello 辞职",
        "2024 — Unity 6 发布（回归数字版本号），Matt Bromberg 任新 CEO，全面取消 Runtime Fee"
    ]:
        b(bullet(text_el(item)))

    b(heading(2, "1.2 现状（2025）"))
    for item in [
        "最新版本：Unity 6（LTS），主要特性包括 GPU Resident Drawer、Adaptive Probe Volumes、WebGPU 预览",
        "市场占有率：全球移动游戏 50-70%，VR/AR 内容占主导地位",
        "月活跃创作者：约 150-200 万",
        "营收：FY2023 约 $21.9 亿（含 IronSource），FY2024 约 $18-20 亿",
        "员工：高峰 8000+ 人，2024 年裁员约 25%（~1800 人），当前约 5000-5500 人",
        "AI 工具：Unity Muse（AI 辅助创作）、Unity Sentis（端侧 ML 推理引擎）、Unity AI（Beta，集成第三方模型）"
    ]:
        b(bullet(text_el(item)))

    b(heading(2, "1.3 竞争格局"))
    b(heading(3, "Unity vs Unreal Engine"))
    for item in [
        "Unreal Engine 5（Epic Games）：AAA 级图形（Nanite、Lumen、MetaHuman），C++/Blueprints，收入 $100 万以下免费，之后 5% 分成",
        "Unity 优势：移动端、独立游戏、VR/AR、2D 游戏、学习曲线低、Asset Store 生态成熟",
        "Unreal 优势：电影级渲染、大型开放世界、主机/PC AAA 项目",
        "代表作 — Unity：Genshin Impact、Pokemon GO、Hollow Knight、Beat Saber",
        "代表作 — Unreal：Fortnite、Hogwarts Legacy、Final Fantasy VII Remake"
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "Unity vs Godot"))
    for item in [
        "Godot：MIT 开源，100% 免费，无供应商锁定",
        "2023 年 Runtime Fee 事件后，Godot 下载量和 GitHub Stars 暴涨",
        "Godot 4.x 的 3D 能力持续增强，但生态和 AAA 支持仍远不及 Unity"
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "其他竞品"))
    for item in [
        "CryEngine（Crytek）：图形强大但社区极小，已边缘化",
        "Cocos Creator（触控科技）：在中国小游戏市场（微信小游戏）份额极高，开源轻量",
        "O3DE（Linux Foundation / 前 Amazon Lumberyard）：Apache 2.0 开源，但生态极不成熟"
    ]:
        b(bullet(text_el(item)))

    b(heading(2, "1.4 中国区情况"))
    for item in [
        "Unity China（合资公司）：2019-2020 年成立，2022 年融资约 $10 亿（阿里巴巴、中国移动、OPPO 参投），估值约 $20 亿",
        "团结引擎（Tuanjie Engine）：Unity 的中国特供版，支持微信小游戏导出、鸿蒙 HarmonyOS、国内云服务集成",
        "miHoYo（HoYoverse）：《原神》《崩坏3》《崩坏：星穹铁道》均使用 Unity，是 Unity 最重要的 AAA 级标杆",
        "其他中国 Unity 大作：明日方舟（Hypergryph）、碧蓝航线、AFK Arena（莉莉丝）、万国觉醒",
        "竞争压力：Cocos Creator 在微信小游戏领域份额极高；Unreal 在高端中国游戏中份额上升"
    ]:
        b(bullet(text_el(item)))

    b(heading(2, "1.5 商业模式"))
    b(heading(3, "许可证体系"))
    for item in [
        "Personal（免费）：年收入 <$20 万，需显示 Unity 启动画面",
        "Pro（~$2,040/年/席位）：年收入 >$20 万，无启动画面，高级支持",
        "Enterprise（定制价格）：大型组织，源码访问，专属支持",
        "Industry（定制价格）：非游戏行业（汽车、影视、建筑）"
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "收入来源"))
    for item in [
        "订阅收入（Create Solutions）：引擎许可，核心业务",
        "广告平台（Grow Solutions / IronSource）：Unity Ads、LevelPlay 广告中介、Tapjoy — 占总收入 50%+",
        "Unity Gaming Services（UGS）：多人网络、云存储、分析、Vivox 语音",
        "Asset Store：6 万+ 资产，Unity 抽成 30%",
        "行业解决方案：汽车 HMI、建筑可视化、影视虚拟制作、数字孪生",
        "AI 产品：Unity Muse、Unity Sentis、Unity AI（Unity Points 计费）"
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "Runtime Fee 事件（2023.9）"))
    b(para(text_el("2023 年 9 月 Unity 宣布按安装量收费（$0.01-$0.20/次），引发全行业强烈抗议。开发者指责其追溯已发布游戏、计费模型不合理。CEO Riccitiello 于 10 月辞职。新 CEO Matt Bromberg 于 2024 年 9 月彻底取消 Runtime Fee，改为常规订阅涨价。")))

    b(divider())

    # ===== Part 2: Technical Deep Dive =====
    b(heading(1, "二、Unity 技术详解"))
    b(heading(2, "2.1 核心架构"))

    b(heading(3, "渲染管线（Render Pipeline）"))
    for item in [
        "Built-in Render Pipeline（旧版）：前向/延迟渲染，最大社区知识库，不基于 SRP",
        "URP（Universal Render Pipeline）：SRP 架构，面向移动/VR/全平台，性能优先，支持 Shader Graph、2D Renderer",
        "HDRP（High Definition Render Pipeline）：SRP 架构，面向高端 PC/主机，PBR 光照、体积雾、DXR 光追、SSGI"
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "DOTS（Data-Oriented Technology Stack）"))
    for item in [
        "ECS（Entity Component System）：Entity + IComponentData + System 架构，数据连续存储（Archetype），缓存友好",
        "Job System：安全多线程，IJob / IJobParallelFor，每 CPU 核心一个 Worker Thread",
        "Burst Compiler：基于 LLVM 的 AOT 编译器，将 IL 编译为 SSE/NEON/WASM 原生代码，性能接近手写 C++",
        "Unity Mathematics：float3/float4x4/quaternion 等高性能数学库"
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "脚本后端"))
    for item in [
        "Mono：JIT 编译，迭代快，用于 Editor 和开发构建",
        "IL2CPP：AOT 编译（IL → C++ → 原生），iOS/主机/WebGL 必需，性能更高，代码更安全"
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "C# 脚本"))
    b(para(text_el("Unity 使用 C# 作为唯一脚本语言。核心生命周期：Awake() → OnEnable() → Start() → Update() → FixedUpdate() → LateUpdate() → OnDisable() → OnDestroy()。支持 Coroutine、async/await（Unity 2023+ 原生 Awaitable）、Assembly Definition 分模块编译。")))

    b(heading(2, "2.2 开发工作流"))
    for item in [
        "Unity Editor：Scene View、Game View、Inspector、Hierarchy、Profiler、Frame Debugger",
        "Scene / Prefab 系统：嵌套 Prefab、Prefab Variants、Additive Scene Loading",
        "Asset Pipeline v2：并行导入、ScriptedImporter、按平台纹理压缩（ASTC/BC/ETC2）",
        "Package Manager（UPM）：Unity Registry / Git URL / 本地包，manifest.json 管理依赖",
        "Addressables：基于 AssetBundle 的高级资源管理，按 Key/Label 加载，支持远程热更新",
        "New Input System：Action-based，设备无关，支持手柄/键盘/触屏自动切换",
        "Physics：3D 用 NVIDIA PhysX，2D 用 Box2D",
        "UI 系统：UI Toolkit（类 Web 的 USS/UXML/Flexbox）和 UGUI（Canvas/RectTransform/TextMeshPro）"
    ]:
        b(bullet(text_el(item)))

    b(heading(2, "2.3 部署与平台"))
    b(para(text_el("Unity 支持 20+ 平台部署：")))
    for item in [
        "桌面：Windows、macOS（Universal Binary）、Linux",
        "移动：iOS、Android（ARM64/ARMv7）",
        "主机：PS4/PS5、Xbox One/Series X|S、Nintendo Switch",
        "Web：WebGL（Emscripten + IL2CPP → WASM），WebGPU 预览中",
        "XR：Meta Quest 2/3/Pro、Apple Vision Pro（PolySpatial）、HoloLens 2、PSVR2，统一使用 OpenXR",
        "嵌入式：Embedded Linux、QNX（汽车座舱）"
    ]:
        b(bullet(text_el(item)))

    b(heading(3, "移动构建要点"))
    for item in [
        "Scripting Backend：IL2CPP（iOS 强制，Android 推荐）",
        "Code Stripping：Medium/High 级别，配合 link.xml 保留必要类型",
        "压缩：LZ4HC（最终构建），纹理 ASTC",
        "优化：Static/Dynamic Batching、LOD Groups、Occlusion Culling、Shader Variants Stripping"
    ]:
        b(bullet(text_el(item)))

    b(heading(2, "2.4 游戏之外的行业应用"))
    for item in [
        "建筑/AEC：Unity Reflect 实时 BIM 数据流（Revit/SketchUp → Unity），AR/VR 建筑漫游",
        "汽车：HMI 座舱界面设计（BMW、Volvo、Hyundai），3D 配置器，QNX/嵌入式 Linux 部署",
        "影视/VFX：虚拟制作（LED Volume）、Cinemachine 虚拟相机、Timeline 动画编排",
        "数字孪生：IoT 数据实时可视化，Pixyz 插件导入 CAD 数据（CATIA/STEP/JT）",
        "仿真训练：军事模拟、医疗手术训练、自动驾驶仿真（ML-Agents + Perception Package）"
    ]:
        b(bullet(text_el(item)))

    b(heading(2, "2.5 开发者生态"))
    for item in [
        "Unity Learn：免费学习平台，结构化路径（Essentials → Junior Programmer → VR Development）",
        "Asset Store：6 万+ 资产，热门：DOTween、Odin Inspector、PlayMaker、Mirror Networking",
        "社区：Unity Forums、Reddit r/Unity3D（50 万+）、Stack Overflow unity3d 标签、官方 Discord",
        "认证：Unity Certified User / Programmer / Artist / Expert（Pearson VUE 考试）",
        "大会：Unite（年度开发者大会，全球多地举办）"
    ]:
        b(bullet(text_el(item)))

    b(divider())

    # ===== Part 3: Sample Project =====
    b(heading(1, "三、开发项目示例：Coin Collector 移动游戏"))
    b(para(text_el("以下是一个完整的 Unity 3D 移动游戏示例 — 玩家在 3D 场景中移动收集金币，包含计分 UI。")))

    b(heading(2, "3.1 项目目录结构"))
    b(code_block("text", """MyCoinCollector/
├── Assets/
│   ├── Scenes/         (MainMenu.unity, GameScene.unity)
│   ├── Scripts/
│   │   ├── Player/     (PlayerController.cs, PlayerHealth.cs)
│   │   ├── Collectibles/ (Coin.cs)
│   │   ├── Managers/   (GameManager.cs, ScoreManager.cs)
│   │   └── UI/         (ScoreDisplay.cs, MainMenuUI.cs)
│   ├── Prefabs/        (Player.prefab, Coin.prefab, Ground.prefab)
│   ├── Materials/      (PlayerMat.mat, CoinMat.mat)
│   ├── Art/            (Textures/, Models/)
│   ├── Audio/          (Music/, SFX/)
│   ├── Input/          (PlayerInputActions.inputactions)
│   └── Settings/       (URP Pipeline Assets)
├── Packages/manifest.json
└── ProjectSettings/"""))

    b(heading(2, "3.2 核心脚本"))
    b(heading(3, "PlayerController.cs"))
    b(code_block("csharp", """using UnityEngine;
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
}"""))

    b(heading(3, "Coin.cs"))
    b(code_block("csharp", """using UnityEngine;

public class Coin : MonoBehaviour
{
    [SerializeField] private float rotateSpeed = 90f;
    [SerializeField] private int scoreValue = 10;
    [SerializeField] private AudioClip pickupSound;

    private void Update() => transform.Rotate(Vector3.up, rotateSpeed * Time.deltaTime);

    private void OnTriggerEnter(Collider other) {
        if (!other.CompareTag("Player")) return;
        if (pickupSound) AudioSource.PlayClipAtPoint(pickupSound, transform.position);
        ScoreManager.Instance.AddScore(scoreValue);
        Destroy(gameObject);
    }
}"""))

    b(heading(3, "ScoreManager.cs"))
    b(code_block("csharp", """using UnityEngine;
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
}"""))

    b(divider())

    # ===== Part 4: AI Impact =====
    b(heading(1, "四、AI 对 Unity 及 3D 行业的影响与展望"))

    b(heading(2, "4.1 Unity 官方 AI 工具"))
    for item in [
        "Unity AI（Beta）：集成在 Editor 中的 AI 助手，基于第三方 Generative AI 模型，支持自动化任务、资产生成、上下文辅助开发。使用 Unity Points 计费体系。",
        "Unity Muse：Unity 自研第一方模型，提供纹理生成、Sprite 生成、Chat-based 代码辅助",
        "Unity Sentis：端侧 ML 推理引擎，支持 ONNX 模型在 Unity Runtime 中运行，用于游戏内 AI（NPC 行为、风格迁移、语音识别等）",
        "ML-Agents Toolkit：强化学习训练框架，用于训练游戏 AI、自动化测试、仿真"
    ]:
        b(bullet(text_el(item)))

    b(heading(2, "4.2 AI 在游戏开发中的应用"))
    for item in [
        "程序化内容生成（PCG）：AI 驱动的关卡设计、地形生成、任务系统",
        "AI NPC 行为：大语言模型驱动的动态对话、自适应难度、情感反应系统",
        "AI 资产生成：Stability AI / Midjourney 生成纹理和概念图，3D 模型生成（Meshy、Tripo3D）",
        "AI 动画：动作捕捉替代方案，基于物理的角色动画（Ziva Dynamics），文本到动画",
        "AI 辅助编程：GitHub Copilot、Claude 等 AI 编程助手大幅提升 Unity C# 开发效率",
        "AI 测试：自动化 QA、AI 驱动的游戏平衡测试、玩家行为模拟"
    ]:
        b(bullet(text_el(item)))

    b(heading(2, "4.3 行业趋势与展望"))
    for item in [
        "Generative AI 正在重塑游戏开发流水线 — 从概念到原型的周期大幅缩短",
        "独立开发者受益最大：AI 工具使 1-3 人团队能完成过去需要 10+ 人的工作",
        "AAA 工作室更审慎：关注 AI 版权风险、艺术质量一致性、工会影响",
        "AI-Native 游戏成为新品类：每个玩家体验独特的个性化内容、实时生成的故事叙事",
        "Unity 的 AI 战略：从 Muse/Sentis 到完整的 Unity AI 平台，目标是让 AI 成为 Editor 的核心组成",
        "风险：AI 生成内容的同质化、版权法律灰色地带、对初级开发者就业的潜在影响",
        "长期展望：3D 引擎将从「工具」进化为「AI 协作平台」，开发者角色从「手工编码」转向「意图驱动」"
    ]:
        b(bullet(text_el(item)))

    b(divider())

    # ===== Part 5: References =====
    b(heading(1, "五、参考信源"))
    refs = [
        ("Unity Official", "https://unity.com"),
        ("Unity 6 Announcement", "https://unity.com/unity-6"),
        ("Unity AI Products", "https://unity.com/ai"),
        ("Unity Docs", "https://docs.unity3d.com/Manual/"),
        ("Unity Blog", "https://unity.com/blog"),
        ("Runtime Fee Cancellation", "https://blog.unity.com/news/unity-is-canceling-the-runtime-fee"),
        ("Unity China / Tuanjie", "https://unity.cn"),
        ("Unity Asset Store", "https://assetstore.unity.com"),
        ("Unity Learn", "https://learn.unity.com"),
        ("Unreal Engine (Competitor)", "https://www.unrealengine.com"),
        ("Godot Engine (Competitor)", "https://godotengine.org"),
        ("O3DE (Competitor)", "https://o3de.org"),
        ("Cocos Creator (Competitor)", "https://www.cocos.com"),
        ("Unity IPO / Financials (SEC)", "https://investors.unity.com"),
        ("Wikipedia - Unity Technologies", "https://en.wikipedia.org/wiki/Unity_Technologies"),
        ("Wikipedia - Unity (game engine)", "https://en.wikipedia.org/wiki/Unity_(game_engine)"),
        ("GDC / Game Developer", "https://www.gamedeveloper.com"),
        ("VentureBeat Gaming", "https://venturebeat.com/games/"),
    ]
    for i, (name, url) in enumerate(refs, 1):
        b(para(text_el(f"{i}. {name} — "), text_el(url, link=url)))

    b(divider())
    b(para(text_el("报告生成时间：2026-03-05 | 数据截止：2025 年初 | 建议核实最新财务数据于 ", bold=False),
           text_el("investors.unity.com", link="https://investors.unity.com")))

    return blocks

if __name__ == "__main__":
    print("Getting Feishu token...")
    token = get_token()
    print(f"Token: {token[:20]}...")

    print("Building report blocks...")
    blocks = build_report()
    print(f"Total blocks: {len(blocks)}")

    print("Writing to Feishu document...")
    add_blocks(token, blocks)

    print(f"\nDone! Document URL: https://bytedance.feishu.cn/docx/{DOC_ID}")
