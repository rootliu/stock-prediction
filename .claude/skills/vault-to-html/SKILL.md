---
name: vault-to-html
description: Render an entire Obsidian vault into one self-contained, professional HTML site — full-text search, tag cloud, reverse-chronological timeline, and a keynote homepage (research insights + auto-extracted quote wall). Opens in Chrome, works offline, commits to git.
user_invocable: true
---

# Obsidian Vault → 单文件 HTML 文档站

把整个 Obsidian vault 渲染成**一个自包含的 HTML 文件**（内嵌全部笔记 + 搜索索引），Chrome 直接打开、可离线、可进 git。配套脚本 `build_vault_site.py` 已随 skill 一起提供。

## 用法

`/vault-to-html` — 用默认 vault 生成并在 Chrome 打开
`/vault-to-html /path/to/vault` — 指定 vault 目录
`/vault-to-html rebuild` — 笔记更新后重新生成（最常用）

## 何时用

- 用户想把 Obsidian 笔记变成一个可分享/可浏览的网页文档
- 想要带搜索、标签、时间线的只读知识库视图
- 笔记更新后刷新这个站点

## 成品特性

单文件 `vault-site.html` 包含三个视图 + 全局搜索：

1. **首页（Keynote）**：一句话主轴横幅 + 数据统计；研究总览的核心洞察卡片（点击跳对应笔记）；**金句墙**（从全 vault 自动提炼的研究论断，点击跳来源）。
2. **时间线**：按月**倒序**（最新在上）展示有日期的笔记，四色类型标签（精读/arXiv/日记/提及），竖向时间轴。
3. **阅读**：左侧分组目录树（研究原则/概念/论文/日记/历史脉络/索引）+ 右侧 Markdown 渲染。
4. **搜索**：标题/正文/标签三路加权，结果带高亮 snippet；`/` 聚焦、`Esc` 清除。
5. **侧栏**：索引目录在上，标签云（Top 40）在下。

设计：深色专业主题（teal→blue 渐变主色）、玻璃态 topbar、卡片 hover 动效、圆角描边表格、自定义滚动条。

---

## 执行步骤

### 1. 定位 vault + 脚本

- 默认 vault：`/Users/rootliu/Documents/Obsidian Vault`（按机器调整；可用 `find ~ -name ".obsidian" -type d` 探测）。
- 脚本：本 skill 目录下的 `build_vault_site.py`。**首选把它复制到 vault 根目录**（这样它能默认用自身所在目录当 vault，且随 vault 一起进 git，跨机可复现）：
  ```bash
  cp "<skill_dir>/build_vault_site.py" "<vault>/build_vault_site.py"
  ```

### 2. 生成 HTML

脚本接受 vault 路径参数（省略则用脚本所在目录）：
```bash
# 脚本在 vault 根目录时（推荐）：
cd "<vault>" && python3 build_vault_site.py

# 或从任意位置指定 vault：
python3 "<skill_dir>/build_vault_site.py" "<vault>" --out "<vault>/vault-site.html"
```
可选参数：`--overview 研究总览.md`（洞察来源笔记）、`--skip 子目录1,子目录2`（额外跳过的目录）。

输出：`<vault>/vault-site.html`（单文件，通常几百 KB）。

### 3. 在 Chrome 打开

```bash
open -a "Google Chrome" "<vault>/vault-site.html"
```

### 4. 校验（生成后必做）

确认内嵌 JSON payload 完好、无 `</script>` 泄漏、关键 UI 锚点都在：
```bash
python3 - <<'EOF'
import re, json
h = open("<vault>/vault-site.html", encoding="utf-8").read()
m = re.search(r'<script id="data"[^>]*>(.*?)</script>', h, re.DOTALL)
d = json.loads(m.group(1).replace("<\\/", "</"))
print("docs:", d["docCount"], "| tags:", len(d["tags"]),
      "| insights:", len(d["insights"]), "| quotes:", len(d["quoteWall"]),
      "| timeline months:", len(d["timeline"]))
assert "</script>" not in m.group(1), "raw </script> leaked into payload!"
for n in ["renderHome", "renderTimeline", "renderReader", "renderMd"]:
    assert n in h, f"missing {n}"
print("OK")
EOF
```

### 5. 提交到 git（vault 仓库）

HTML 和脚本放在 vault 仓库里一起 push（vault 在 `~/Documents/` 需 `dangerouslyDisableSandbox`，走 `GIT_SSL_NO_VERIFY=1`，见 [[sync-obsidian]]）：
```bash
cd "<vault>"
git add build_vault_site.py vault-site.html
git commit -m "chore: rebuild vault-site.html"
GIT_SSL_NO_VERIFY=1 git push
```

---

## 脚本工作原理（便于改造）

`build_vault_site.py` 是纯 Python 标准库（无依赖），流程：

1. **collect()**：递归扫描 `.md`，跳过 `.git/.obsidian/.trash` 和已有独立 reader 的目录。
2. **解析每篇**：
   - `split_frontmatter` 拆 YAML frontmatter。
   - `parse_tags`：frontmatter `tags:` + 正文 `#tag`（过滤纯数字/单字母/标题误判）。
   - `title_of`：取 H1；若 H1 等于文件名（本 vault 论文笔记惯例）且有 frontmatter `title`，组合成「中文名 · 英文 title」。
   - `extract_date`：5 级优先级 — 日记文件名 > frontmatter date_read/date > 正文"精读日期" > arXiv YYMM > 正文任意 YYYY-MM-DD。
   - `extract_quotes`：抓「可引用句」「> **加粗整句**」「整行加粗结论」「核心论断：…」，再用 `_is_quote_like` 过滤术语标签/元数据行/半截句/冒号结尾小标题。
   - `group_of`：按文件名前缀分组。
3. **extract_insights**：从 `研究总览.md` 的 `### N. 标题` 切出洞察 + 首段摘要。
4. **timeline**：按 `YYYY-MM` 分桶，**月份和月内都倒序**（最新在上）。
5. **渲染**：把 `DATA`（docs/insights/quoteWall/tags/timeline）序列化进 `<script type="application/json">`，前端 JS 做 markdown 渲染 + 路由 + 搜索。

### 调整要点

- **金句太少/太多**：改 `extract_quotes` 的正则或 `_is_quote_like` 的过滤阈值（中文句长 ≥18、冒号结尾排除等）。
- **洞察来源换笔记**：`--overview` 参数，或改 `extract_insights` 的 `### N.` 匹配。
- **时间线顺序**：`timeline` 构建处的两个 `reverse=True`（月份 + 月内）。倒序是默认；改成正序去掉 `reverse=True`。
- **配色/样式**：HTML 模板顶部 `:root` CSS 变量（`--accent`、`--grad` 等）。
- **侧栏顺序**：`renderSide()` 里先「索引目录」后「标签云」；分组顺序在 `order` 数组。

## 注意

- 脚本默认跳过 `AI-Agentic-架构整理/`（那里已有独立的 reader.html）。用 `--skip` 加更多。
- 前端 markdown 渲染是轻量自实现（标题/列表/表格/代码块/引用/`[[wikilink]]`/`**bold**`/`==mark==`），不支持复杂嵌套；够日常研究笔记用。
- `[[wikilink]]` 按笔记标题匹配跳转；匹配不到显示为灰色 missing 链接。
- 每次笔记有更新就重跑脚本刷新——它是幂等的，整库重新扫描。
