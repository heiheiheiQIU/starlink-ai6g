"""
报告 Word 构建脚本 v2（官方版式参考文档 + pandoc 转换 + 后处理）。
版式依据：官方模板（页边距上下2.5cm/左右3cm、正文宋体小四、一级黑体三号居中、
二级黑体四号、三级黑体小四）；后处理：表格居中、独立公式自动编号（1）（2）…、
标题统一黑色。
用法: python scripts/build_report_docx.py [md源] [输出docx]
"""

import subprocess
import sys
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "docs" / "report"
REFERENCE = REPORT_DIR / "reference_official.docx"

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def ensure_reference_doc() -> Path:
    if REFERENCE.exists():
        return REFERENCE
    raw = subprocess.run(
        ["pandoc", "--print-default-data-file", "reference.docx"],
        capture_output=True,
    )
    if raw.returncode != 0:
        raise RuntimeError(f"无法生成参考文档: {raw.stderr.decode(errors='ignore')}")
    REFERENCE.write_bytes(raw.stdout)

    d = docx.Document(str(REFERENCE))

    for section in d.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3)
        section.right_margin = Cm(3)

    def set_font(style, east_asia, size, bold=None):
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        rpr = style.element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = rpr.makeelement(qn("w:rFonts"), {})
            rpr.append(rfonts)
        rfonts.set(qn("w:eastAsia"), east_asia)
        if bold is not None:
            style.font.bold = bold

    styles = d.styles
    normal = styles["Normal"]
    set_font(normal, "宋体", 12)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(0)
    ind = normal.paragraph_format.element.get_or_add_pPr()
    ind.append(ind.makeelement(qn("w:ind"), {qn("w:firstLineChars"): "200"}))

    set_font(styles["Title"], "黑体", 22)
    styles["Title"].paragraph_format.alignment = 1

    set_font(styles["Heading 1"], "黑体", 16)
    styles["Heading 1"].paragraph_format.alignment = 1
    styles["Heading 1"].paragraph_format.space_before = Pt(14)
    styles["Heading 1"].paragraph_format.space_after = Pt(10)

    set_font(styles["Heading 2"], "黑体", 14)
    styles["Heading 2"].paragraph_format.space_before = Pt(10)
    styles["Heading 2"].paragraph_format.space_after = Pt(6)

    set_font(styles["Heading 3"], "黑体", 12)
    styles["Heading 3"].paragraph_format.space_before = Pt(8)
    styles["Heading 3"].paragraph_format.space_after = Pt(4)

    set_font(styles["Heading 4"], "黑体", 12)
    set_font(styles["Compact"], "宋体", 10.5)
    if "Table" in [s.name for s in styles]:
        set_font(styles["Table"], "宋体", 10.5)

    d.save(str(REFERENCE))
    return REFERENCE


def postprocess(out: Path) -> None:
    d = docx.Document(str(out))
    w_ns = {"w": W_NS, "m": M_NS}

    # 1) 表格居中
    for table in d.tables:
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # 2) 独立公式编号：含 m:oMath 且无 w:t 文本的段落
    text_width = Cm(15)
    half = Cm(7.5)
    number = 0
    for para in d.paragraphs:
        has_math = para._p.findall(".//m:oMath", w_ns)
        has_text = para._p.findall(".//w:t", w_ns)
        if not has_math or has_text:
            continue
        number += 1
        para.paragraph_format.tab_stops.clear_all()
        para.paragraph_format.tab_stops.add_tab_stop(half, WD_TAB_ALIGNMENT.CENTER)
        para.paragraph_format.tab_stops.add_tab_stop(text_width, WD_TAB_ALIGNMENT.RIGHT)
        # pandoc 将独立公式写为 m:oMathPara（无 w:r 包裹）——在数学元素前插入前置制表位
        math_el = para._p.find(".//m:oMathPara", w_ns) or para._p.find(".//m:oMath", w_ns)
        if math_el is None:
            continue
        tab_run = math_el.makeelement(qn("w:r"), {})
        tab_text = math_el.makeelement(qn("w:t"), {})
        tab_text.text = "\t"
        tab_run.append(tab_text)
        math_el.addprevious(tab_run)
        run = para.add_run(f"\t({number})")
        run.font.size = Pt(12)

    d.save(str(out))
    print(f"[build] 独立公式编号 {number} 条")


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else REPORT_DIR / "report_v2.md"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else REPORT_DIR / "星地智调_作品方案_v2.docx"
    reference = ensure_reference_doc()
    result = subprocess.run(
        ["pandoc", str(source), "--reference-doc", str(reference), "-o", str(out)],
        capture_output=True,
    )
    if result.returncode != 0:
        print(result.stderr.decode(errors="ignore"))
        return 1
    postprocess(out)
    d = docx.Document(str(out))
    print(f"[build] {out} 完成：段落 {len(d.paragraphs)}、表格 {len(d.tables)}（已居中）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
