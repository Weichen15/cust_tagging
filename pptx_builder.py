from datetime import date
from io import BytesIO
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

# 色系設定
COLOR_TITLE_BG = RGBColor(0x1F, 0x45, 0x7E)   # 深藍
COLOR_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
COLOR_ACCENT = RGBColor(0x2E, 0x86, 0xC1)      # 中藍
COLOR_LIGHT_BG = RGBColor(0xF0, 0xF4, 0xF8)    # 淺藍灰
COLOR_TEXT = RGBColor(0x2C, 0x3E, 0x50)        # 深灰藍


def _set_cell_bg(cell, color: RGBColor):
    from pptx.oxml.ns import qn
    from lxml import etree
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    solidFill = etree.SubElement(tcPr, qn("a:solidFill"))
    srgbClr = etree.SubElement(solidFill, qn("a:srgbClr"))
    srgbClr.set("val", f"{color[0]:02X}{color[1]:02X}{color[2]:02X}")


def _add_slide(prs, layout_idx=6):
    layout = prs.slide_layouts[layout_idx]
    return prs.slides.add_slide(layout)


def _add_textbox(slide, left, top, width, height, text, font_size=18,
                 bold=False, color=COLOR_TEXT, align=PP_ALIGN.LEFT, bg_color=None):
    txBox = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    if bg_color:
        fill = txBox.fill
        fill.solid()
        fill.fore_color.rgb = bg_color
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color
    return txBox


def build_pptx(data: dict) -> BytesIO:
    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    label = data.get("label", "")
    summary = data.get("summary", "")
    categories = data.get("categories", [])
    today = date.today().strftime("%Y/%m/%d")

    # === Slide 1: 封面 ===
    slide1 = _add_slide(prs)
    bg = slide1.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = COLOR_TITLE_BG

    _add_textbox(slide1, 0.8, 1.8, 11.7, 1.5,
                 f"客戶樣貌標籤分析", font_size=36, bold=True,
                 color=COLOR_WHITE, align=PP_ALIGN.CENTER)
    _add_textbox(slide1, 0.8, 3.4, 11.7, 1.0,
                 f"標籤：{label}", font_size=28, bold=True,
                 color=RGBColor(0xAE, 0xD6, 0xF1), align=PP_ALIGN.CENTER)
    _add_textbox(slide1, 0.8, 4.6, 11.7, 0.6,
                 today, font_size=16,
                 color=RGBColor(0xCC, 0xCC, 0xCC), align=PP_ALIGN.CENTER)

    # === Slide 2: 標籤說明 + 分類總覽 ===
    slide2 = _add_slide(prs)
    bg2 = slide2.background
    bg2.fill.solid()
    bg2.fill.fore_color.rgb = COLOR_LIGHT_BG

    _add_textbox(slide2, 0.5, 0.3, 12.3, 0.7,
                 f"標籤說明：{label}", font_size=22, bold=True,
                 color=COLOR_TITLE_BG)
    _add_textbox(slide2, 0.5, 1.1, 12.3, 1.0,
                 summary, font_size=16, color=COLOR_TEXT)

    _add_textbox(slide2, 0.5, 2.2, 12.3, 0.5,
                 "涵蓋分類", font_size=18, bold=True, color=COLOR_ACCENT)

    cat_y = 2.8
    for i, cat in enumerate(categories):
        store_count = len(cat.get("stores", []))
        _add_textbox(slide2, 0.8, cat_y, 11.8, 0.45,
                     f"▸  {cat['category_name']}（{store_count} 家）",
                     font_size=15, color=COLOR_TEXT)
        cat_y += 0.48
        if cat_y > 6.8:
            break

    # === Slide 3+: 各分類店家明細 ===
    for cat in categories:
        slide = _add_slide(prs)
        bg_s = slide.background
        bg_s.fill.solid()
        bg_s.fill.fore_color.rgb = COLOR_LIGHT_BG

        cat_name = cat.get("category_name", "")
        reason = cat.get("reason", "")
        stores = cat.get("stores", [])

        _add_textbox(slide, 0.5, 0.25, 12.3, 0.65,
                     cat_name, font_size=22, bold=True, color=COLOR_TITLE_BG)
        _add_textbox(slide, 0.5, 0.95, 12.3, 0.6,
                     f"挑選原因：{reason}", font_size=13,
                     color=RGBColor(0x55, 0x66, 0x77))

        if not stores:
            continue

        # 表格
        rows = min(len(stores), 12) + 1
        table = slide.shapes.add_table(
            rows, 3,
            Inches(0.5), Inches(1.7),
            Inches(12.3), Inches(min(rows * 0.42, 5.5))
        ).table

        headers = ["店家 / 品牌", "說明", "資料來源"]
        col_widths = [Inches(3.5), Inches(5.0), Inches(3.8)]
        for i, w in enumerate(col_widths):
            table.columns[i].width = w

        for j, h in enumerate(headers):
            cell = table.cell(0, j)
            cell.text = h
            _set_cell_bg(cell, COLOR_TITLE_BG)
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            run = p.runs[0] if p.runs else p.add_run()
            run.font.bold = True
            run.font.color.rgb = COLOR_WHITE
            run.font.size = Pt(13)

        for r, store in enumerate(stores[:12], start=1):
            row_data = [
                store.get("name", ""),
                store.get("note", ""),
                store.get("source", ""),
            ]
            bg = COLOR_LIGHT_BG if r % 2 == 0 else COLOR_WHITE
            for c, val in enumerate(row_data):
                cell = table.cell(r, c)
                cell.text = str(val)
                _set_cell_bg(cell, bg)
                p = cell.text_frame.paragraphs[0]
                run = p.runs[0] if p.runs else p.add_run()
                run.font.size = Pt(11)
                run.font.color.rgb = COLOR_TEXT

    # === 最後一頁：備註 ===
    slide_last = _add_slide(prs)
    bg_l = slide_last.background
    bg_l.fill.solid()
    bg_l.fill.fore_color.rgb = COLOR_TITLE_BG

    _add_textbox(slide_last, 0.8, 2.5, 11.7, 1.0,
                 "備註", font_size=28, bold=True,
                 color=COLOR_WHITE, align=PP_ALIGN.CENTER)
    _add_textbox(slide_last, 0.8, 3.6, 11.7, 1.5,
                 "• 本份分析由 AI 自動產生，店家清單僅供參考，請依實際資料庫比對後調整\n"
                 "• SAS 特店中文名稱需依實際資料庫欄位格式微調",
                 font_size=15, color=RGBColor(0xAE, 0xD6, 0xF1))

    buf = BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf
