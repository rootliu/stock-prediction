#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_vault_site.py — 把整个 Obsidian vault 渲染成一个自包含的 HTML 文档站。

输出：vault-site.html （单文件，内嵌全部笔记 + 搜索索引；Chrome 直接打开，可离线）

特性：
  - 全文搜索（标题/正文/标签）
  - 标签筛选（frontmatter tags + 正文 #tag）
  - 首页 Keynote 高亮：研究总览 14 条洞察 + 全 vault 金句墙
  - Markdown 渲染（标题/列表/表格/代码块/引用/[[wikilink]]/**加粗**/`code`/高亮 ==mark==）
  - [[wikilink]] 点击跳转到对应笔记
  - 双栏：左侧分组目录树，右侧阅读区
用法：
  python3 build_vault_site.py [VAULT_DIR] [--out OUTPUT.html] [--overview 研究总览.md]
  # 省略 VAULT_DIR 时，默认用脚本所在目录（适合把脚本放进 vault 根目录直接跑）。
"""
import os, re, json, html, datetime, sys, argparse

sys.stdout.reconfigure(encoding="utf-8")

_p = argparse.ArgumentParser(description="Render an Obsidian vault into a single self-contained HTML site.")
_p.add_argument("vault", nargs="?", default=os.path.dirname(os.path.abspath(__file__)),
                help="vault 根目录（默认：脚本所在目录）")
_p.add_argument("--out", default=None, help="输出 HTML 路径（默认：<vault>/vault-site.html）")
_p.add_argument("--overview", default="研究总览.md", help="洞察来源笔记文件名（默认 研究总览.md）")
_p.add_argument("--skip", default="", help="额外跳过的子目录，逗号分隔")
_args = _p.parse_args()

VAULT = os.path.abspath(_args.vault)
OUT = _args.out or os.path.join(VAULT, "vault-site.html")
SKIP_DIRS = {".git", ".obsidian", ".trash", "AI-Agentic-架构整理"}  # 后者已有独立 reader
SKIP_DIRS |= {s.strip() for s in _args.skip.split(",") if s.strip()}
OVERVIEW = _args.overview

# ---------- 收集 markdown 文件 ----------
def collect():
    docs = []
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in files:
            if not fn.endswith(".md"):
                continue
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, VAULT)
            with open(full, encoding="utf-8") as f:
                raw = f.read()
            docs.append({"file": rel, "raw": raw})
    return docs

# ---------- frontmatter ----------
def split_frontmatter(raw):
    fm = {}
    body = raw
    if raw.startswith("---"):
        m = re.match(r"^---\n(.*?)\n---\n?(.*)$", raw, re.DOTALL)
        if m:
            head, body = m.group(1), m.group(2)
            for line in head.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    fm[k.strip()] = v.strip()
    return fm, body

def parse_tags(fm, body):
    tags = set()
    # frontmatter tags: [a, b] 或 yaml list
    t = fm.get("tags", "")
    if t:
        t = t.strip().strip("[]")
        for part in re.split(r"[,，]", t):
            part = part.strip().strip("'\"")
            if part:
                tags.add(part)
    # 正文 #tag：要求 # 前是空白/行首，标签是合理的 hashtag（不含 / 结尾、不是纯数字、不以数字开头）
    for m in re.finditer(r"(?:^|\s)#([A-Za-z一-鿿][\w一-鿿\-]{1,28})\b", body):
        tag = m.group(1)
        if re.match(r"^[0-9]+$", tag):      # 纯数字
            continue
        if re.match(r"^[A-Za-z]$", tag):    # 单字母
            continue
        tags.add(tag)
    return sorted(tags)

def extract_date(fm, body, fname):
    """返回 (date_str 'YYYY-MM-DD' 或 'YYYY-MM', kind)。优先级：精读日期 > frontmatter date > 日记文件名 > arXiv YYMM > 正文日期。"""
    base = os.path.basename(fname)
    # 1) 日记文件名
    m = re.match(r"^(\d{4}-\d{2}-\d{2})\.md$", base)
    if m:
        return m.group(1), "journal"
    # 2) frontmatter 精读/阅读/日期
    for key in ("date_read_v3", "date_read_v2", "date_read", "date_paper", "date"):
        v = fm.get(key, "").strip().strip("'\"")
        m = re.search(r"(\d{4}-\d{2}-\d{2})", v)
        if m:
            return m.group(1), "read"
        m = re.search(r"(\d{4}-\d{2})", v)
        if m:
            return m.group(1), "read"
    # 3) 正文「精读日期 / 阅读日期：YYYY-MM-DD」
    m = re.search(r"(?:精读日期|阅读日期|date_read|精读)[：:\s]*?(\d{4}-\d{2}-\d{2})", body)
    if m:
        return m.group(1), "read"
    # 4) arXiv YYMM → 论文发表月（从文件名或正文）
    m = re.search(r"(\d{2})(\d{2})\.\d{4,5}", base) or re.search(r"arXiv[:\s]*(\d{2})(\d{2})\.\d{4,5}", body)
    if m:
        yy, mm = m.group(1), m.group(2)
        if 20 <= int(yy) <= 27 and 1 <= int(mm) <= 12:
            return f"20{yy}-{mm}", "arxiv"
    # 5) 正文任意 YYYY-MM-DD（取最早一个有意义的）
    m = re.search(r"(20[0-9]{2}-[01][0-9]-[0-3][0-9])", body)
    if m:
        return m.group(1), "body"
    return None, None

def title_of(fm, body, fname):
    stem = os.path.splitext(os.path.basename(fname))[0]
    fm_title = fm.get("title", "").strip().strip("'\"")
    m = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    h1 = m.group(1).strip() if m else None
    # 若 H1 就是文件名（本 vault 论文笔记的惯例），用 中文名 · 英文标题 组合
    if h1 and h1 == stem and fm_title:
        zh = re.sub(r"^论文-", "", stem)
        zh = re.sub(r"-\d{4}\.\d{4,5}$|-[A-Z]{3,}$", "", zh)
        return zh.strip() + " · " + fm_title
    if h1:
        return h1
    if fm_title:
        return fm_title
    return stem

# ---------- 分组 ----------
def group_of(fname, title):
    base = os.path.basename(fname)
    if "/" in fname and fname.startswith("论文-2026前"):
        return "📚 历史脉络 (2026前)"
    if re.match(r"^\d{4}-\d{2}-\d{2}\.md$", base):
        return "📅 日记 Journal"
    if base.startswith("研究原则") or base.startswith("研究总览"):
        return "🎯 研究原则 / 总览"
    if base in ("索引.md",):
        return "🗂️ 索引"
    if base.startswith("论文-"):
        return "📄 论文笔记"
    return "🧠 概念与主题"

# ---------- 金句提取 ----------
def _clean(s):
    s = s.strip().strip("“”\"")
    s = re.sub(r"\[\[([^\]|]+)\|?([^\]]*)\]\]", lambda m: (m.group(2) or m.group(1)).strip(), s)  # 去 wikilink 语法
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"\*\*", "", s)   # 去残留加粗标记
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def _is_quote_like(s):
    """过滤：术语词条（X：定义）、半截句、标签式。要求像一句完整论断。"""
    if not s:
        return False
    # 词条式：前 24 字内出现「(英文缩写)」+ 冒号 → 多半是术语解释
    if re.match(r"^[A-Za-z][\w\s]*\([^)]+\)\s*[：:]", s):
        return False
    # 冒号结尾 = 标签/小标题（"验证器（Verifiers）：" / "代码作为接口具有三个关键属性："）
    if re.search(r"[：:]\s*$", s):
        return False
    # 元数据行（arXiv / 作者 / 机构 / 同源对照 / 页数）
    if re.search(r"(arXiv\s*[:：]|作者\s*[:：]|机构\s*[:：]|同源对照|\d+\s*页)", s):
        return False
    # 编号开头的列表项（"1. COT 特征…"）多半是要点而非金句——除非很完整
    # （保留：这些其实是不错的结论，不滤）
    # 纯术语/名词短语（无句读、无动词感、无箭头）：排除 bold 术语标签如 "Terminal-Bench"
    has_punct = bool(re.search(r"[，,。.；;—…→（）()]", s))
    cjk = len(re.findall(r"[一-鿿]", s))
    if not has_punct and "→" not in s:
        if cjk < 18:
            return False
    return True

def extract_quotes(title, body):
    quotes = []
    lines = body.splitlines()
    def add(s):
        if 14 <= len(s) <= 200 and _is_quote_like(s) and "：" not in s[:8]:
            quotes.append(s)
    for i, ln in enumerate(lines):
        st = ln.strip()
        # 1) "可引用句" / "金句" 后跟一句
        if "可引用句" in st or ("金句" in st and len(st) < 12):
            for j in range(i+1, min(i+4, len(lines))):
                s = _clean(re.sub(r"^[>*\-\s]+", "", lines[j].strip()))
                if 8 <= len(s) <= 220 and _is_quote_like(s):
                    quotes.append(s); break
            continue
        # 2) > **加粗整句** 引用
        m = re.match(r"^>\s*\*\*(.+?)\*\*\s*$", st)
        if m:
            add(_clean(m.group(1))); continue
        # 3) 整行就是一个加粗结论句：**……**（独占一行）
        m = re.match(r"^\*\*(.+?)\*\*[。.!！]?$", st)
        if m:
            add(_clean(m.group(1))); continue
        # 4) "核心论断/核心洞察/一句话(定位)：xxx" 行内冒号式金句
        m = re.match(r"^[>\-*\s]*\**(核心论断|核心洞察|核心判断|一句话[^：:]*|关键论点|本质)\**\s*[：:]\s*(.+)$", st)
        if m:
            s = _clean(m.group(2))
            if 10 <= len(s) <= 220 and _is_quote_like(s):
                quotes.append(s)
            continue
    # 优先完整句（以句末标点结尾的排前面）
    def complete(s): return bool(re.search(r"[。.!！?？”\"]$", s)) or "→" in s
    quotes.sort(key=lambda s: (0 if complete(s) else 1))
    seen, out = set(), []
    for q in quotes:
        key = q[:40]
        if key not in seen:
            seen.add(key); out.append(q)
    return out[:5]

# ---------- 研究总览 14 洞察 ----------
def extract_insights(docs):
    ov = next((d for d in docs if os.path.basename(d["file"]) == OVERVIEW), None)
    if not ov:
        return []
    _, body = split_frontmatter(ov["raw"])
    insights = []
    blocks = re.split(r"^### (\d+)\.\s+(.+)$", body, flags=re.MULTILINE)
    # blocks: [pre, num, title, content, num, title, content, ...]
    for k in range(1, len(blocks)-2, 3):
        num = blocks[k]; ttl = blocks[k+1].strip(); content = blocks[k+2].strip()
        # 取第一段为摘要
        para = content.split("\n\n")[0].strip()
        para = re.sub(r"\s+", " ", para)
        insights.append({"num": int(num), "title": ttl, "summary": para})
    return insights

# ---------- 主流程 ----------
docs_raw = collect()
docs = []
all_tags = {}
for d in sorted(docs_raw, key=lambda x: x["file"]):
    fm, body = split_frontmatter(d["raw"])
    title = title_of(fm, body, d["file"])
    tags = parse_tags(fm, body)
    quotes = extract_quotes(title, body)
    grp = group_of(d["file"], title)
    date, dkind = extract_date(fm, body, d["file"])
    doc_id = "d" + str(len(docs))
    for t in tags:
        all_tags[t] = all_tags.get(t, 0) + 1
    docs.append({
        "id": doc_id, "file": d["file"], "title": title,
        "group": grp, "tags": tags, "content": body, "quotes": quotes,
        "date": date, "dkind": dkind,
    })

insights = extract_insights(docs_raw)

# 金句墙：聚合所有 quotes（带来源）
quote_wall = []
for doc in docs:
    for q in doc["quotes"]:
        quote_wall.append({"q": q, "src": doc["title"], "docId": doc["id"]})

# 标签按频次排序
tag_list = sorted(all_tags.items(), key=lambda kv: (-kv[1], kv[0]))

# 时间线：按 YYYY-MM 分桶，桶内按日期排序
def month_key(date):
    return date[:7] if date else None
timeline_docs = [d for d in docs if d["date"]]
months = {}
for d in timeline_docs:
    mk = month_key(d["date"])
    months.setdefault(mk, []).append(d)
timeline = []
for mk in sorted(months.keys(), reverse=True):           # 月份倒序：最新在上
    items = sorted(months[mk], key=lambda d: d["date"], reverse=True)  # 月内倒序
    timeline.append({
        "month": mk,
        "items": [{"id": d["id"], "title": d["title"], "date": d["date"],
                   "kind": d["dkind"], "group": d["group"]} for d in items],
    })

DATA = {
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    "docCount": len(docs),
    "docs": docs,
    "insights": insights,
    "quoteWall": quote_wall,
    "tags": tag_list,
    "timeline": timeline,
}

payload = json.dumps(DATA, ensure_ascii=False)

# ---------- HTML 模板 ----------
HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>研究 Vault · 知识库</title>
<style>
:root{
  --bg:#0c1117; --bg2:#0a0e13; --panel:#141b24; --panel2:#1a232e; --panel3:#202b38;
  --ink:#e9eef5; --ink2:#c4cedb; --muted:#8595a6; --faint:#5e6b7a;
  --line:#222d3a; --line2:#2c3a49;
  --accent:#54d9c9; --accent-d:#2ba596; --accent2:#f3ad5c; --accent3:#7fa8ec; --accent4:#e88fb0;
  --grad:linear-gradient(135deg,#54d9c9,#7fa8ec);
  --grad2:linear-gradient(135deg,#f3ad5c,#e88fb0);
  --mark:#ffe27a; --markbg:rgba(255,226,122,.15); --soft:#10302c;
  --shadow:0 8px 30px rgba(0,0,0,.4); --shadow-lg:0 20px 60px rgba(0,0,0,.5);
  --r:14px;
  font-family:"Inter","Segoe UI Variable","PingFang SC","Microsoft YaHei",system-ui,sans-serif;
}
*{box-sizing:border-box;}
html,body{height:100%;}
body{margin:0;background:
  radial-gradient(1200px 600px at 80% -10%,rgba(84,217,201,.06),transparent 60%),
  radial-gradient(900px 500px at 0% 110%,rgba(127,168,236,.06),transparent 55%),
  var(--bg);
  color:var(--ink);font-size:14.5px;line-height:1.65;-webkit-font-smoothing:antialiased;}
button,input,select{font:inherit;color:inherit;}
button{cursor:pointer;border:none;background:none;}
a{color:var(--accent3);text-decoration:none;}
a:hover{text-decoration:underline;}
::selection{background:rgba(84,217,201,.28);}
/* scrollbars */
*::-webkit-scrollbar{width:10px;height:10px;}
*::-webkit-scrollbar-thumb{background:var(--line2);border-radius:8px;border:2px solid var(--bg);}
*::-webkit-scrollbar-thumb:hover{background:var(--faint);}

.app{min-height:100vh;display:grid;grid-template-rows:auto 1fr;}
/* ---------- topbar ---------- */
.topbar{position:sticky;top:0;z-index:40;display:flex;gap:18px;align-items:center;
  padding:13px 22px;border-bottom:1px solid var(--line);
  background:linear-gradient(180deg,rgba(12,17,23,.96),rgba(12,17,23,.82));backdrop-filter:blur(14px) saturate(140%);}
.brand{display:flex;align-items:center;gap:11px;min-width:210px;}
.logo{width:34px;height:34px;border-radius:9px;background:var(--grad);display:grid;place-items:center;
  font-weight:800;color:#06201d;font-size:16px;box-shadow:0 4px 14px rgba(84,217,201,.35);}
.brand h1{margin:0;font-size:16.5px;font-weight:750;letter-spacing:.2px;}
.brand small{display:block;color:var(--muted);font-size:11px;font-weight:500;margin-top:-1px;}
.search{flex:1;display:flex;align-items:center;gap:9px;background:var(--panel2);
  border:1px solid var(--line2);border-radius:11px;padding:9px 14px;max-width:580px;transition:border-color .15s,box-shadow .15s;}
.search:focus-within{border-color:var(--accent-d);box-shadow:0 0 0 3px rgba(84,217,201,.12);}
.search svg{width:16px;height:16px;color:var(--muted);flex:none;}
.search input{flex:1;background:none;border:none;outline:none;font-size:14px;}
.search input::placeholder{color:var(--faint);}
.search kbd{font-size:10.5px;color:var(--faint);border:1px solid var(--line2);border-radius:5px;padding:1px 6px;background:var(--bg);}
.search .x{color:var(--muted);font-size:17px;line-height:1;padding:0 2px;}
.nav{display:flex;gap:4px;background:var(--panel2);padding:4px;border-radius:11px;border:1px solid var(--line);}
.nav button{padding:7px 15px;font-size:13px;color:var(--muted);border-radius:8px;font-weight:560;transition:.15s;}
.nav button:hover{color:var(--ink2);}
.nav button.on{color:#06201d;background:var(--grad);box-shadow:0 3px 10px rgba(84,217,201,.3);font-weight:680;}

/* ---------- layout ---------- */
.main{display:grid;grid-template-columns:300px 1fr;min-height:0;}
.side{border-right:1px solid var(--line);background:linear-gradient(180deg,var(--panel),var(--bg2));
  overflow-y:auto;max-height:calc(100vh - 60px);padding:6px 0 50px;}
.side .sec{padding:14px 14px 4px;}
.side h3{font-size:10.5px;text-transform:uppercase;letter-spacing:1.4px;color:var(--faint);
  margin:6px 6px 9px;display:flex;align-items:center;gap:7px;font-weight:700;}
.side h3::after{content:"";flex:1;height:1px;background:var(--line);}
.tree-grp{margin-bottom:3px;}
.tree-grp>.g-title{font-size:12px;font-weight:700;color:var(--accent2);padding:7px 10px 4px;
  display:flex;justify-content:space-between;align-items:center;}
.tree-grp>.g-title span{color:var(--faint);font-weight:600;font-size:10.5px;}
.tree-item{display:block;padding:6px 10px 6px 20px;font-size:12.8px;color:var(--ink2);
  border-radius:8px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  position:relative;transition:.12s;margin:1px 6px;}
.tree-item::before{content:"";position:absolute;left:9px;top:50%;width:4px;height:4px;border-radius:50%;
  background:var(--line2);transform:translateY(-50%);transition:.12s;}
.tree-item:hover{background:var(--panel3);color:#fff;}
.tree-item:hover::before{background:var(--accent);}
.tree-item.on{background:linear-gradient(90deg,var(--soft),transparent);color:var(--accent);font-weight:640;}
.tree-item.on::before{background:var(--accent);box-shadow:0 0 8px var(--accent);}
.tagcloud{display:flex;flex-wrap:wrap;gap:6px;padding:2px 8px;}

/* ---------- tags ---------- */
.tag{background:var(--panel2);border:1px solid var(--line2);border-radius:999px;
  padding:3px 11px;font-size:11.5px;color:var(--ink2);cursor:pointer;transition:.13s;white-space:nowrap;}
.tag:hover{border-color:var(--accent-d);color:#fff;transform:translateY(-1px);}
.tag.on{background:var(--grad);color:#06201d;border-color:transparent;font-weight:700;}
.tag b{opacity:.5;font-weight:600;margin-left:5px;}

.content{overflow-y:auto;max-height:calc(100vh - 60px);}
.wrap{max-width:880px;margin:0 auto;padding:32px 40px 100px;}

/* ---------- home / keynote ---------- */
.hero{max-width:1140px;margin:0 auto;padding:34px 40px 10px;}
.axis{position:relative;border-radius:18px;padding:30px 34px;margin-bottom:30px;overflow:hidden;
  background:linear-gradient(135deg,rgba(84,217,201,.10),rgba(127,168,236,.08));
  border:1px solid var(--line2);box-shadow:var(--shadow-lg);}
.axis::before{content:"";position:absolute;inset:0;border-radius:18px;padding:1px;
  background:var(--grad);-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);
  -webkit-mask-composite:xor;mask-composite:exclude;opacity:.5;pointer-events:none;}
.axis .lbl{font-size:11px;letter-spacing:3px;text-transform:uppercase;color:var(--accent);font-weight:700;}
.axis p{margin:12px 0 0;font-size:22px;font-weight:720;line-height:1.5;letter-spacing:.2px;
  background:linear-gradient(120deg,#fff,#cfe7e2);-webkit-background-clip:text;background-clip:text;color:transparent;}
.stats{display:flex;gap:26px;margin:20px 0 4px;flex-wrap:wrap;}
.stat{display:flex;flex-direction:column;}
.stat b{font-size:24px;font-weight:780;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;line-height:1;}
.stat span{font-size:11.5px;color:var(--muted);margin-top:4px;letter-spacing:.5px;}

.sec-h{font-size:16px;font-weight:760;margin:36px 0 16px;display:flex;align-items:center;gap:11px;letter-spacing:.3px;}
.sec-h .bar{width:5px;height:20px;background:var(--grad2);border-radius:3px;}
.sec-h .cnt{font-size:12px;color:var(--faint);font-weight:600;}

.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:15px;}
.card{position:relative;background:linear-gradient(160deg,var(--panel),var(--bg2));
  border:1px solid var(--line);border-radius:var(--r);padding:18px 19px;cursor:pointer;
  transition:transform .14s,border-color .14s,box-shadow .14s;overflow:hidden;}
.card::after{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--grad);opacity:0;transition:.14s;}
.card:hover{transform:translateY(-3px);border-color:var(--line2);box-shadow:var(--shadow);}
.card:hover::after{opacity:1;}
.card .n{font-size:11px;color:var(--accent);font-weight:780;letter-spacing:1px;}
.card .t{font-size:14.5px;font-weight:700;margin:6px 0 8px;line-height:1.4;}
.card .s{font-size:12.6px;color:var(--muted);line-height:1.58;
  display:-webkit-box;-webkit-line-clamp:5;-webkit-box-orient:vertical;overflow:hidden;}

.qwall{columns:2;column-gap:15px;}
@media(max-width:820px){.qwall{columns:1;}}
.quote{break-inside:avoid;position:relative;background:linear-gradient(160deg,var(--panel),var(--bg2));
  border:1px solid var(--line);border-radius:var(--r);padding:18px 18px 15px;margin-bottom:15px;cursor:pointer;transition:.14s;}
.quote:hover{border-color:var(--accent4);transform:translateY(-2px);box-shadow:var(--shadow);}
.quote .mark{font-size:34px;line-height:0;color:var(--accent4);opacity:.5;font-family:Georgia,serif;}
.quote .qt{font-size:14px;line-height:1.62;color:var(--ink);margin-top:6px;}
.quote .qs{font-size:11.5px;color:var(--muted);margin-top:11px;display:flex;align-items:center;gap:6px;}
.quote .qs::before{content:"";width:14px;height:1px;background:var(--accent4);}

/* ---------- timeline ---------- */
.tlwrap{max-width:1000px;margin:0 auto;padding:30px 40px 100px;}
.tl{position:relative;margin-left:8px;padding-left:34px;}
.tl::before{content:"";position:absolute;left:7px;top:6px;bottom:6px;width:2px;
  background:linear-gradient(180deg,var(--accent),var(--accent3),var(--accent4));border-radius:2px;opacity:.5;}
.tl-month{position:relative;margin-bottom:30px;}
.tl-month>.m-label{position:relative;font-size:13px;font-weight:780;color:var(--accent2);margin-bottom:13px;letter-spacing:.5px;}
.tl-month>.m-label::before{content:"";position:absolute;left:-34px;top:3px;width:14px;height:14px;border-radius:50%;
  background:var(--bg);border:3px solid var(--accent2);box-shadow:0 0 0 4px rgba(243,173,92,.12);}
.tl-item{position:relative;background:linear-gradient(160deg,var(--panel),var(--bg2));border:1px solid var(--line);
  border-radius:11px;padding:11px 15px;margin-bottom:9px;cursor:pointer;transition:.13s;
  display:flex;align-items:center;gap:13px;}
.tl-item::before{content:"";position:absolute;left:-31px;top:50%;width:8px;height:8px;border-radius:50%;
  background:var(--line2);transform:translateY(-50%);transition:.13s;}
.tl-item:hover{border-color:var(--line2);transform:translateX(3px);box-shadow:var(--shadow);}
.tl-item:hover::before{background:var(--accent);box-shadow:0 0 8px var(--accent);}
.tl-item .d{font-size:11px;color:var(--faint);font-variant-numeric:tabular-nums;min-width:74px;font-weight:600;}
.tl-item .ti{flex:1;font-size:13.2px;font-weight:580;color:var(--ink);}
.tl-item .k{font-size:10px;padding:2px 8px;border-radius:999px;font-weight:680;white-space:nowrap;}
.k.read{background:rgba(84,217,201,.15);color:var(--accent);}
.k.arxiv{background:rgba(127,168,236,.15);color:var(--accent3);}
.k.journal{background:rgba(243,173,92,.15);color:var(--accent2);}
.k.body{background:var(--panel3);color:var(--muted);}

/* ---------- tag bar (reader) ---------- */
.tagbar{display:flex;flex-wrap:wrap;gap:7px;padding:13px 18px;border-bottom:1px solid var(--line);
  background:linear-gradient(180deg,var(--panel),transparent);align-items:center;}
.tagbar .meta{font-size:11.5px;color:var(--faint);margin-right:6px;}

/* ---------- markdown ---------- */
.md{font-size:15px;}
.md h1{font-size:27px;margin:.1em 0 .6em;font-weight:800;letter-spacing:.2px;
  background:linear-gradient(120deg,#fff,#bfe0db);-webkit-background-clip:text;background-clip:text;color:transparent;}
.md h2{font-size:20px;margin:1.5em 0 .55em;padding-bottom:.3em;border-bottom:1px solid var(--line);font-weight:740;}
.md h3{font-size:16.5px;margin:1.25em 0 .45em;font-weight:720;color:var(--accent2);}
.md h4{font-size:14.5px;margin:1.05em 0 .3em;font-weight:720;color:var(--accent3);}
.md p{margin:.65em 0;color:var(--ink2);}
.md ul,.md ol{margin:.5em 0;padding-left:1.5em;}
.md li{margin:.3em 0;color:var(--ink2);}
.md li::marker{color:var(--accent-d);}
.md strong,.md b{color:var(--ink);font-weight:700;}
.md code{background:var(--panel2);border:1px solid var(--line2);border-radius:6px;padding:1.5px 6px;
  font-family:"SF Mono",Menlo,Consolas,monospace;font-size:12.6px;color:var(--accent);}
.md pre{background:linear-gradient(160deg,var(--panel2),var(--bg2));border:1px solid var(--line2);
  border-radius:12px;padding:15px 17px;overflow-x:auto;margin:1em 0;box-shadow:inset 0 1px 0 rgba(255,255,255,.03);}
.md pre code{background:none;border:none;padding:0;color:var(--ink2);font-size:12.8px;line-height:1.6;}
.md blockquote{margin:.9em 0;padding:10px 18px;border-left:3px solid var(--accent);
  background:linear-gradient(90deg,var(--soft),transparent);border-radius:0 10px 10px 0;color:#cfe3df;}
.md blockquote p{color:#cfe3df;margin:.3em 0;}
.md table{border-collapse:separate;border-spacing:0;width:100%;margin:1.1em 0;font-size:13px;
  display:block;overflow-x:auto;border:1px solid var(--line2);border-radius:10px;}
.md th,.md td{border-bottom:1px solid var(--line);border-right:1px solid var(--line);padding:8px 12px;text-align:left;vertical-align:top;}
.md tr:last-child td{border-bottom:none;}
.md th:last-child,.md td:last-child{border-right:none;}
.md th{background:var(--panel2);font-weight:720;color:var(--ink);position:sticky;top:0;}
.md tbody tr:hover{background:rgba(84,217,201,.04);}
.md mark{background:var(--markbg);color:var(--mark);padding:0 4px;border-radius:4px;font-weight:600;}
.md a.wl{color:var(--accent);border-bottom:1px dashed var(--accent-d);font-weight:560;}
.md a.wl:hover{background:rgba(84,217,201,.1);border-radius:3px;text-decoration:none;}
.md a.wl.missing{color:var(--faint);border-bottom-style:dotted;cursor:default;}
.md hr{border:none;border-top:1px solid var(--line);margin:1.6em 0;}
.doc-head .crumb{font-size:11.5px;color:var(--faint);letter-spacing:.3px;display:flex;align-items:center;gap:7px;}
.doc-head .crumb .dt{color:var(--accent3);}

/* ---------- search results ---------- */
.hit{font-size:12.5px;color:var(--muted);padding:14px 20px 6px;letter-spacing:.3px;}
.hit b{color:var(--accent);}
.reslist{padding:0 12px;}
.ritem{padding:14px 16px;border-radius:11px;cursor:pointer;transition:.12s;margin-bottom:4px;border:1px solid transparent;}
.ritem:hover{background:var(--panel);border-color:var(--line);}
.ritem .rt{font-weight:680;font-size:14.5px;}
.ritem .rg{font-size:11px;color:var(--faint);margin-left:8px;font-weight:500;}
.ritem .rs{font-size:12.5px;color:var(--muted);margin-top:5px;line-height:1.55;}
.ritem mark{background:var(--markbg);color:var(--mark);padding:0 2px;border-radius:3px;}
.empty{color:var(--muted);padding:60px;text-align:center;font-size:14px;}
.empty .big{font-size:40px;opacity:.4;margin-bottom:10px;}

@media(max-width:760px){
  .main{grid-template-columns:1fr;}
  .side{display:none;}
  .hero,.tlwrap,.wrap{padding-left:20px;padding-right:20px;}
}
</style>
</head>
<body>
<div class="app">
  <div class="topbar">
    <div class="brand">
      <div class="logo">研</div>
      <div><h1>研究 Vault</h1><small id="meta"></small></div>
    </div>
    <div class="search">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
      <input id="q" placeholder="搜索标题 / 正文 / 标签…" autocomplete="off">
      <kbd id="kbd">/</kbd>
      <button class="x" id="qx" title="清除" style="display:none">×</button>
    </div>
    <div class="nav">
      <button data-view="home" class="on">首页</button>
      <button data-view="timeline">时间线</button>
      <button data-view="reader">阅读</button>
    </div>
  </div>
  <div class="main">
    <aside class="side" id="side"></aside>
    <section class="content" id="content"></section>
  </div>
</div>
<script id="data" type="application/json">__PAYLOAD__</script>
<script>
const DATA=JSON.parse(document.getElementById("data").textContent);
const state={view:"home",q:"",tag:"",active:DATA.docs[0]&&DATA.docs[0].id};
document.getElementById("meta").textContent=DATA.docCount+" 篇 · "+DATA.tags.length+" 标签";
const titleById={};DATA.docs.forEach(d=>titleById[d.title]=d.id);
const KIND={read:"精读",arxiv:"arXiv",journal:"日记",body:"提及"};

function esc(s){return (s||"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));}
function tokenize(s){return (s||"").toLowerCase().split(/\s+/).filter(Boolean);}

/* ---------- markdown ---------- */
function inline(t){
  let s=esc(t);
  s=s.replace(/`([^`]+)`/g,(m,c)=>"<code>"+c+"</code>");
  s=s.replace(/==([^=]+)==/g,(m,c)=>"<mark>"+c+"</mark>");
  s=s.replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>");
  s=s.replace(/(?<![*\w])\*([^*\n]+)\*(?![*\w])/g,"<i>$1</i>");
  s=s.replace(/\[\[([^\]|]+)\|?([^\]]*)\]\]/g,(m,tgt,lbl)=>{
    tgt=tgt.trim();const label=(lbl||tgt).trim();const anchor=tgt.split("#")[0].trim();
    const id=titleById[anchor];
    if(id)return '<a class="wl" data-doc="'+id+'">'+esc(label)+'</a>';
    return '<a class="wl missing" title="未找到笔记">'+esc(label)+'</a>';
  });
  s=s.replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');
  return s;
}
function renderMd(md){
  const lines=md.split("\n");let html="",i=0;
  while(i<lines.length){
    let ln=lines[i];
    if(/^```/.test(ln)){let code=[];i++;while(i<lines.length&&!/^```/.test(lines[i])){code.push(lines[i]);i++;}i++;html+="<pre><code>"+esc(code.join("\n"))+"</code></pre>";continue;}
    let h=ln.match(/^(#{1,6})\s+(.+)$/);
    if(h){const lv=h[1].length;html+="<h"+lv+">"+inline(h[2])+"</h"+lv+">";i++;continue;}
    if(/^\s*\|.*\|\s*$/.test(ln)&&i+1<lines.length&&/^\s*\|[\s:|-]+\|\s*$/.test(lines[i+1])){
      let rows=[ln];i+=2;while(i<lines.length&&/^\s*\|.*\|\s*$/.test(lines[i])){rows.push(lines[i]);i++;}
      const cells=r=>r.split("|").slice(1,-1).map(c=>c.trim());
      const head=cells(rows[0]);
      html+="<table><thead><tr>"+head.map(c=>"<th>"+inline(c)+"</th>").join("")+"</tr></thead><tbody>";
      for(let r=1;r<rows.length;r++){html+="<tr>"+cells(rows[r]).map(c=>"<td>"+inline(c)+"</td>").join("")+"</tr>";}
      html+="</tbody></table>";continue;
    }
    if(/^>\s?/.test(ln)){let bq=[];while(i<lines.length&&/^>\s?/.test(lines[i])){bq.push(lines[i].replace(/^>\s?/,""));i++;}html+="<blockquote>"+bq.map(inline).join("<br>")+"</blockquote>";continue;}
    if(/^\s*[-*+]\s+/.test(ln)){let items=[];while(i<lines.length&&/^\s*[-*+]\s+/.test(lines[i])){items.push(lines[i].replace(/^\s*[-*+]\s+/,""));i++;}html+="<ul>"+items.map(x=>"<li>"+inline(x)+"</li>").join("")+"</ul>";continue;}
    if(/^\s*\d+\.\s+/.test(ln)){let items=[];while(i<lines.length&&/^\s*\d+\.\s+/.test(lines[i])){items.push(lines[i].replace(/^\s*\d+\.\s+/,""));i++;}html+="<ol>"+items.map(x=>"<li>"+inline(x)+"</li>").join("")+"</ol>";continue;}
    if(/^(-{3,}|\*{3,})\s*$/.test(ln)){html+="<hr>";i++;continue;}
    if(ln.trim()===""){i++;continue;}
    let para=[ln];i++;while(i<lines.length&&lines[i].trim()!==""&&!/^(#{1,6}\s|>|\s*[-*+]\s|\s*\d+\.\s|```|\s*\|)/.test(lines[i])){para.push(lines[i]);i++;}
    html+="<p>"+para.map(inline).join("<br>")+"</p>";
  }
  return html;
}

/* ---------- sidebar: 索引在上, 标签云在下 ---------- */
function renderSide(){
  const groups={};
  DATA.docs.forEach(d=>{(groups[d.group]=groups[d.group]||[]).push(d);});
  const order=["🎯 研究原则 / 总览","🧠 概念与主题","📄 论文笔记","📅 日记 Journal","📚 历史脉络 (2026前)","🗂️ 索引"];
  let h='<div class="sec"><h3>📑 索引目录</h3>';
  order.forEach(g=>{
    if(!groups[g])return;
    h+='<div class="tree-grp"><div class="g-title">'+g+'<span>'+groups[g].length+'</span></div>';
    groups[g].sort((a,b)=>a.title.localeCompare(b.title,"zh"));
    groups[g].forEach(d=>{h+='<span class="tree-item'+(state.active===d.id&&state.view==="reader"?" on":"")+'" data-doc="'+d.id+'">'+esc(d.title)+'</span>';});
    h+='</div>';
  });
  h+='</div>';
  h+='<div class="sec"><h3>🏷️ 标签云</h3><div class="tagcloud">';
  DATA.tags.slice(0,40).forEach(([t,c])=>{h+='<span class="tag'+(state.tag===t?" on":"")+'" data-tag="'+esc(t)+'">'+esc(t)+'<b>'+c+'</b></span>';});
  h+='</div></div>';
  document.getElementById("side").innerHTML=h;
}

/* ---------- home ---------- */
function renderHome(){
  let h='<div class="hero">';
  h+='<div class="axis"><div class="lbl">一句话主轴</div><p>Agentic AI 的关键变化，不是模型从聊天变得更会聊天，而是模型被放进了一个可记忆、可调用工具、可执行、可审计、可治理的架构里。</p>';
  h+='<div class="stats">'
    +'<div class="stat"><b>'+DATA.docCount+'</b><span>笔记</span></div>'
    +'<div class="stat"><b>'+DATA.insights.length+'</b><span>核心洞察</span></div>'
    +'<div class="stat"><b>'+DATA.quoteWall.length+'</b><span>金句</span></div>'
    +'<div class="stat"><b>'+DATA.tags.length+'</b><span>标签</span></div>'
    +'<div class="stat"><b>'+DATA.timeline.length+'</b><span>时间跨月</span></div>'
    +'</div></div>';
  h+='<div class="sec-h"><span class="bar"></span>研究总览 · 核心洞察<span class="cnt">'+DATA.insights.length+' 条</span></div><div class="cards">';
  const ovId=titleById["研究总览 (Research Overview)"]||titleById["研究总览"]||"";
  DATA.insights.forEach(it=>{h+='<div class="card" data-doc="'+ovId+'"><div class="n">洞察 #'+it.num+'</div><div class="t">'+inline(it.title)+'</div><div class="s">'+inline(it.summary)+'</div></div>';});
  h+='</div>';
  if(DATA.quoteWall.length){
    h+='<div class="sec-h"><span class="bar"></span>金句墙<span class="cnt">'+DATA.quoteWall.length+' 条</span></div><div class="qwall">';
    DATA.quoteWall.forEach(q=>{h+='<div class="quote" data-doc="'+q.docId+'"><div class="mark">”</div><div class="qt">'+inline(q.q)+'</div><div class="qs">'+esc(q.src)+'</div></div>';});
    h+='</div>';
  }
  h+='</div>';
  document.getElementById("content").innerHTML=h;
  document.getElementById("content").scrollTop=0;
}

/* ---------- timeline ---------- */
function renderTimeline(){
  const terms=tokenize(state.q);
  let h='<div class="tlwrap"><div class="sec-h"><span class="bar"></span>研究时间线<span class="cnt">'+DATA.timeline.length+' 个月 · '+DATA.timeline.reduce((a,m)=>a+m.items.length,0)+' 篇</span></div><div class="tl">';
  DATA.timeline.forEach(mo=>{
    const items=mo.items.filter(it=>{if(!terms.length)return true;const t=(it.title).toLowerCase();return terms.some(x=>t.includes(x));});
    if(!items.length)return;
    const [y,m]=mo.month.split("-");
    h+='<div class="tl-month"><div class="m-label">'+y+' 年 '+parseInt(m)+' 月</div>';
    items.forEach(it=>{h+='<div class="tl-item" data-doc="'+it.id+'"><span class="d">'+it.date+'</span><span class="ti">'+esc(it.title)+'</span><span class="k '+it.kind+'">'+KIND[it.kind]+'</span></div>';});
    h+='</div>';
  });
  h+='</div></div>';
  document.getElementById("content").innerHTML=h;
  document.getElementById("content").scrollTop=0;
}

/* ---------- search ---------- */
function searchDocs(){
  const terms=tokenize(state.q);
  return DATA.docs.map(d=>{
    const hay=(d.title+" "+d.tags.join(" ")+" "+d.content).toLowerCase();
    let score=0;terms.forEach(t=>{if(d.title.toLowerCase().includes(t))score+=5;if(d.tags.join(" ").toLowerCase().includes(t))score+=3;if(hay.includes(t))score+=1;});
    return {d,score};
  }).filter(x=>x.score>0).sort((a,b)=>b.score-a.score);
}
function snippet(content,terms){
  const lc=content.toLowerCase();let pos=-1;
  for(const t of terms){const p=lc.indexOf(t);if(p>=0){pos=p;break;}}
  if(pos<0)pos=0;
  let s=esc(content.slice(Math.max(0,pos-45),pos+130).replace(/\n/g," "));
  terms.forEach(t=>{if(t)s=s.replace(new RegExp("("+t.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")+")","ig"),"<mark>$1</mark>");});
  return s;
}
function renderSearch(){
  const terms=tokenize(state.q);const res=searchDocs();
  let h='<div class="hit">找到 <b>'+res.length+'</b> 篇 · 关键词「'+esc(state.q)+'」</div><div class="reslist">';
  if(!res.length)h='<div class="empty"><div class="big">🔍</div>没有匹配「'+esc(state.q)+'」的笔记</div><div class="reslist">';
  res.forEach(({d})=>{h+='<div class="ritem" data-doc="'+d.id+'"><div class="rt">'+esc(d.title)+'<span class="rg">'+esc(d.group)+'</span></div><div class="rs">'+snippet(d.content,terms)+'…</div></div>';});
  h+='</div>';
  document.getElementById("content").innerHTML=h;
  document.getElementById("content").scrollTop=0;
}

/* ---------- reader ---------- */
function renderReader(){
  const d=DATA.docs.find(x=>x.id===state.active)||DATA.docs[0];
  if(!d){document.getElementById("content").innerHTML='<div class="empty">无文档</div>';return;}
  let h='<div class="tagbar"><span class="meta">标签</span>';
  if(d.tags.length)d.tags.forEach(t=>{h+='<span class="tag'+(state.tag===t?" on":"")+'" data-tag="'+esc(t)+'">'+esc(t)+'</span>';});
  else h+='<span style="color:var(--faint);font-size:12px;">无</span>';
  h+='</div><div class="wrap"><div class="doc-head"><div class="crumb">'+esc(d.group)+(d.date?' · <span class="dt">'+d.date+'</span>':'')+' · '+esc(d.file)+'</div></div>';
  h+='<article class="md">'+renderMd(d.content)+'</article></div>';
  document.getElementById("content").innerHTML=h;
  document.getElementById("content").scrollTop=0;
}

/* ---------- router ---------- */
function render(){
  document.querySelectorAll(".nav button").forEach(b=>b.classList.toggle("on",b.dataset.view===state.view));
  document.getElementById("qx").style.display=state.q?"block":"none";
  document.getElementById("kbd").style.display=state.q?"none":"block";
  renderSide();
  if(state.q){renderSearch();return;}
  if(state.view==="home")renderHome();
  else if(state.view==="timeline")renderTimeline();
  else renderReader();
}
function openDoc(id){state.active=id;state.view="reader";state.q="";document.getElementById("q").value="";render();}

document.addEventListener("click",e=>{
  const doc=e.target.closest("[data-doc]");
  if(doc&&doc.dataset.doc){openDoc(doc.dataset.doc);return;}
  const tag=e.target.closest(".tag");
  if(tag){state.tag=tag.dataset.tag;state.q=tag.dataset.tag;document.getElementById("q").value=tag.dataset.tag;state.view="reader";render();return;}
  const nav=e.target.closest(".nav button");
  if(nav){state.view=nav.dataset.view;state.q="";document.getElementById("q").value="";render();}
});
const qinput=document.getElementById("q");
qinput.addEventListener("input",e=>{state.q=e.target.value.trim();state.tag="";render();});
document.getElementById("qx").addEventListener("click",()=>{state.q="";state.tag="";qinput.value="";qinput.focus();render();});
document.addEventListener("keydown",e=>{
  if(e.key==="/"&&document.activeElement!==qinput){e.preventDefault();qinput.focus();}
  if(e.key==="Escape"){state.q="";qinput.value="";qinput.blur();render();}
});
render();
</script>
</body>
</html>
"""

out = HTML.replace("__PAYLOAD__", payload.replace("</", "<\\/"))
with open(OUT, "w", encoding="utf-8") as f:
    f.write(out)

print(f"✓ 生成 {OUT}")
print(f"  {len(docs)} 篇笔记 · {len(tag_list)} 标签 · {len(insights)} 洞察 · {len(quote_wall)} 金句")
