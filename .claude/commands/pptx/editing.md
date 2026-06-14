# Editing Presentations

## Template-Based Workflow（本專案使用 python-pptx）

本專案使用 `pptx_builder.py` + `template.pptx` 搭配 **python-pptx** 產生簡報，
與下方的 unpack/pack XML 流程不同——若要修改 `pptx_builder.py`，請直接用 python-pptx API。

若需要**直接編輯 XML**（例如 debug 投影片結構），才使用下方的解包流程。

---

## python-pptx 修改指引（本專案主要方式）

### 文字替換

```python
def _replace_in_para(para, old: str, new: str):
    full = "".join(r.text for r in para.runs)
    if old not in full:
        return
    new_text = full.replace(old, new)
    if para.runs:
        para.runs[0].text = new_text
        for r in para.runs[1:]:
            r.text = ""
```

- 必須跨 run 合併再替換，否則會漏掉被 PowerPoint 拆開的文字
- 保留第一個 run 的格式

### 動態新增投影片（關鍵）

```python
def _add_slide_from_xml(prs, saved_xml, src_part=None):
    new_slide = prs.slides.add_slide(prs.slide_layouts[6])
    # 複製圖片/媒體 relationships（依 rId 數字排序，確保對應正確）
    if src_part is not None:
        sorted_rels = sorted(src_part.rels.items(), key=lambda x: int(x[0][3:]))
        for rId, rel in sorted_rels:
            if rel.reltype == _LAYOUT_RT:
                continue
            if rel.is_external:
                new_slide.part.rels.get_or_add_ext_rel(rel.reltype, rel.target_ref)
            else:
                new_slide.part.rels.get_or_add(rel.reltype, rel.target_part)
    # 複製 XML...
```

**重要**：必須在 `_delete_slide` **之前** 先把 `src_part` 存起來，刪除後 part 會失效。

### Template 投影片索引（template.pptx）

| Index | 投影片 | 說明 |
|-------|--------|------|
| 0 | 封面 | `"擷取標籤名稱"` 替換標籤 |
| 3 | 敘事說明 | `"針對這個標籤的規畫做一個說明"` |
| 5 | 分類分隔頁（範本） | `"內容1"` 替換分類名 |
| 6 | 分類表格頁（範本） | 13列×3欄表格 |
| 9 | Thank You | 直接複製 |

---

## XML 直接編輯流程（Debug 用）

When using an existing presentation as a template:

1. **Analyze existing slides**:
   ```bash
   python -m markitdown template.pptx
   ```

2. **Unpack**: `python scripts/office/unpack.py template.pptx unpacked/`

3. **Build presentation**:
   - Delete unwanted slides (remove from `<p:sldIdLst>`)
   - Duplicate slides you want to reuse (`add_slide.py`)
   - Reorder slides in `<p:sldIdLst>`
   - **Complete all structural changes before editing content**

4. **Edit content**: Update text in each `slide{N}.xml`.

5. **Clean**: `python scripts/clean.py unpacked/`

6. **Pack**: `python scripts/office/pack.py unpacked/ output.pptx --original template.pptx`

---

## Common Pitfalls

### Multi-Item Content

If source has multiple items (numbered lists, multiple sections), create separate `<a:p>` elements for each — **never concatenate into one string**.

**❌ WRONG**:
```xml
<a:p>
  <a:r><a:rPr .../><a:t>Step 1: Do the first thing. Step 2: Do the second thing.</a:t></a:r>
</a:p>
```

**✅ CORRECT** — separate paragraphs:
```xml
<a:p>
  <a:r><a:rPr lang="zh-TW" sz="2799" b="1" .../><a:t>步驟 1</a:t></a:r>
</a:p>
<a:p>
  <a:r><a:rPr lang="zh-TW" sz="2799" .../><a:t>做第一件事</a:t></a:r>
</a:p>
```

### Smart Quotes in XML

When adding text with quotes, use XML entities:

| Character | XML Entity |
|-----------|------------|
| `"` | `&#x201C;` |
| `"` | `&#x201D;` |
| `'` | `&#x2018;` |
| `'` | `&#x2019;` |

### Whitespace

Use `xml:space="preserve"` on `<a:t>` with leading/trailing spaces.

### XML Parsing

Use `defusedxml.minidom`, not `xml.etree.ElementTree` (corrupts namespaces).
