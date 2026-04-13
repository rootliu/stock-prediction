---
name: organize-obsidian
description: Organize Obsidian vault by extracting topics from daily journals and Zotero papers, building bidirectional links, categorizing by theme, and generating a research overview index.
user_invocable: true
---

# Obsidian Journal & Zotero Paper Organizer

Scan an Obsidian vault for daily journal entries and a Zotero library for academic papers, then organize everything into topic notes with bidirectional `[[wikilinks]]`, categorized paper summaries, and a master research overview index.

## Usage

`/organize-obsidian` — full scan, organize, and index

Optional arguments:
- `/organize-obsidian 2026` — only process papers from a specific year
- `/organize-obsidian journals-only` — only process journal entries, skip Zotero

## Workflow

### Phase 1: Discover Data Sources

#### 1.1 Find Obsidian Vault

```bash
find /Users -name ".obsidian" -type d 2>/dev/null | head -10
```

Then list all `.md` files in the vault root to understand existing structure:

```bash
ls -la "<vault_path>/"
find "<vault_path>" -name "*.md" -not -path "*/.obsidian/*" | sort
```

#### 1.2 Find Zotero Database

```bash
find /Users -name "zotero.sqlite" -type f 2>/dev/null | head -5
```

#### 1.3 Read All Journal Entries

Use the `Read` tool to read each journal `.md` file. Identify:
- Date-based files (e.g., `2026-04-07.md`)
- Existing topic notes
- Existing folder structure

### Phase 2: Extract Zotero Papers

#### 2.1 Query Papers with Metadata

```sql
-- Get papers with title, abstract, date
SELECT i.itemID, iv_title.value as title, iv_abs.value as abstract, iv_date.value as date
FROM items i
LEFT JOIN itemData id_title ON i.itemID = id_title.itemID
  AND id_title.fieldID = (SELECT fieldID FROM fields WHERE fieldName='title')
LEFT JOIN itemDataValues iv_title ON id_title.valueID = iv_title.valueID
LEFT JOIN itemData id_abs ON i.itemID = id_abs.itemID
  AND id_abs.fieldID = (SELECT fieldID FROM fields WHERE fieldName='abstractNote')
LEFT JOIN itemDataValues iv_abs ON id_abs.valueID = iv_abs.valueID
LEFT JOIN itemData id_date ON i.itemID = id_date.itemID
  AND id_date.fieldID = (SELECT fieldID FROM fields WHERE fieldName='date')
LEFT JOIN itemDataValues iv_date ON id_date.valueID = iv_date.valueID
WHERE iv_date.value LIKE '<year>%'
  AND i.itemTypeID NOT IN (
    SELECT itemTypeID FROM itemTypes WHERE typeName IN ('attachment','note')
  )
ORDER BY iv_date.value;
```

#### 2.2 Get Tags for Categorization

```sql
SELECT i.itemID, GROUP_CONCAT(t.name, '; ') as tags
FROM items i
JOIN itemTags it ON i.itemID = it.itemID
JOIN tags t ON it.tagID = t.tagID
WHERE i.itemID IN (<filtered_item_ids>)
GROUP BY i.itemID;
```

#### 2.3 Get Collections (if used)

```sql
SELECT ci.itemID, c.collectionName
FROM collectionItems ci
JOIN collections c ON ci.collectionID = c.collectionID
WHERE ci.itemID IN (<filtered_item_ids>)
ORDER BY ci.itemID;
```

### Phase 3: Analyze & Categorize

#### 3.1 Extract Topics from Journals

For each journal entry, identify:
- **Main topics/concepts** discussed (these become topic notes)
- **Key terms and frameworks** mentioned
- **References to papers or external sources**

#### 3.2 Categorize Papers by Theme

Read all paper titles and abstracts, then cluster into 6-10 thematic categories. Common AI/ML categories include:
- LLM Fundamentals & Scaling
- Reasoning & Chain-of-Thought
- Agent Architecture & Workflow
- Agent Memory Systems
- Training & Alignment
- Multimodal & Vision-Language
- Retrieval & Knowledge Enhancement
- Efficient Inference & Deployment
- Security & Governance
- Domain Applications

**Categorization heuristics:**
- Use paper titles and abstracts as primary signals
- Use Zotero tags as secondary signals
- A paper may appear in multiple categories if strongly relevant
- Group papers by year within each category

#### 3.3 Map Cross-References

Identify connections between:
- Journal topics ↔ Paper categories
- Journal topics ↔ Journal topics
- Paper categories (current year) ↔ Paper categories (previous years)

### Phase 4: Generate Obsidian Files

#### 4.1 Topic Notes (from Journals)

For each major topic identified in journals, create `<Topic Name>.md`:

```markdown
# <Topic Name>

> 来源: [[<YYYY-MM-DD>]]

## 核心观点
<Structured summary of the journal content>

## 相关论文
- [[论文-<Category>]] — <brief connection description>

## 相关主题
- [[<Other Topic>]] — <brief connection description>
```

**Key principles:**
- Preserve all original content and insights
- Add structure (headers, tables, lists) for readability
- Use `[[wikilinks]]` for all cross-references
- Include a "来源" (source) backlink to the original journal entry

#### 4.2 Paper Category Notes

For current year papers, create `论文-<Category>.md` at vault root.
For previous year papers, create `论文-<Year>前/<Category>.md` in a subfolder.

```markdown
# <Category Name>

> 分类：<English Category> | <Year Range> | 共 N 篇

## <Subcategory>

### <Paper Title> (<YYYY-MM>)
<1-3 sentence summary from abstract, highlighting key contribution>

### <Paper Title> (<YYYY-MM>)
<Summary>

## 相关主题
- [[<Topic Note>]] — <connection>
- [[论文-<Other Category>]] — <connection>
- [[论文-<Year>前/<Category>]] — <cross-year connection>
```

**Key principles:**
- Include paper date for temporal context
- Summarize in Chinese (or match the user's language)
- Bold key terms and findings
- Cross-link between current and previous year categories

#### 4.3 Update Daily Notes

Add a structured header to each daily journal with backlinks:

```markdown
# <YYYY-MM-DD> 日记

## 主题笔记
- [[<Topic Note>]] — <brief description>

## 相关论文
- [[论文-<Category>]] — <specific papers related to this day's content>

---

## 原始笔记
<Original content preserved as-is>
```

#### 4.4 Master Summary Index

Create or update `研究总览.md`:

```markdown
# 研究总览 (Research Overview)

> 最后更新: <date> | 论文总数: ~N 篇 | 日记: N 篇

## 核心研究主线
<ASCII diagram showing relationships between major themes>

## 日记索引
| 日期 | 主题 | 关键概念 |
|------|------|----------|
| [[<date>]] | [[<topic>]] | <keywords> |

## <Year> 论文分类 (~N 篇)
| 分类 | 篇数 | 核心关注 |
|------|------|----------|
| [[论文-<Category>]] | N | <focus> |

## <Year>前论文分类 (~N 篇)
| 分类 | 篇数 | 核心关注 | 时间跨度 |
|------|------|----------|----------|
| [[论文-<Year>前/<Category>]] | N | <focus> | <range> |

## 关键洞察摘要
### 1. <Insight title>
<2-3 sentences with [[wikilinks]] to relevant notes>

## 时间线
<ASCII bar chart showing paper distribution over time>
```

### Phase 5: Verify & Report

```bash
# Count all generated files
find "<vault_path>" -name "*.md" -not -path "*/.obsidian/*" | wc -l

# List structure
find "<vault_path>" -name "*.md" -not -path "*/.obsidian/*" | sort
```

Present a summary tree to the user showing:
- Total files created/updated
- File structure overview
- Number of papers processed per category
- Number of bidirectional links created

## Key Lessons & Gotchas

1. **Sandbox restrictions**: Obsidian vaults are typically in `~/Documents/` which requires `dangerouslyDisableSandbox: true` for `mkdir` and may need it for writes. The user can use `/sandbox` to manage restrictions.

2. **Zotero database locking**: `zotero.sqlite` can be locked if Zotero is running. The `sqlite3` read-only query usually works regardless, but if it fails, ask user to close Zotero or use the `-readonly` flag.

3. **Large Zotero libraries**: For libraries with 500+ papers, the full query output may exceed tool limits. Use `LIMIT` and `OFFSET`, or filter by date ranges, and read results in chunks.

4. **Abstract availability**: Not all Zotero papers have abstracts. For papers without abstracts, categorize by title and tags only. Note this in the output.

5. **Duplicate papers**: Zotero may contain duplicate entries (same paper imported multiple times). Deduplicate by title similarity before categorizing.

6. **Obsidian folder creation**: Use `mkdir -p` via Bash for new folders. Obsidian will auto-detect new folders and files on next sync.

7. **Bidirectional link integrity**: Every `[[link]]` target should correspond to an actual file. Before finalizing, verify that all link targets exist as files in the vault.

8. **Language consistency**: Match the user's language. If journals are in Chinese, write summaries and category names in Chinese. If mixed, default to the primary language of the journals.

9. **Preserving original content**: Never modify or delete original journal content. Always keep it under an "原始笔记" section. Only add structure above it.

10. **Incremental updates**: If the vault already has organized content from a previous run, update existing category files rather than creating duplicates. Check for existing files before writing.

11. **Paper categorization is fuzzy**: Some papers fit multiple categories. Mention the paper in its primary category with a full summary, and add a cross-reference line in secondary categories.

12. **Wikilink path format**: For files in subfolders, use `[[folder/filename]]` format. Obsidian resolves these relative to vault root.
