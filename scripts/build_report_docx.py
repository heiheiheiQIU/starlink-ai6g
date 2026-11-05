"""
报告 Word 构建脚本（官方版式参考文档 + pandoc 转换）。
版式依据：官方模板（页边距上下2.5cm/左右3cm、正文宋体小四、一级黑体三号居中、
二级黑体四号、三级黑体小四）；借鉴 CUMCM paper-chief 规范（图表登记、公式核对、文献注册）。
用法: python scripts/build_report_docx.py [md源] [输出docx]
"""

import subprocess
import sys
from pathlib import Path

import docx
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "docs" / "report"
REFERENCE = REPORT_DIR / "reference_official.docx"


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

    # 页面：上下2.5cm、左右3cm（官方模板）
    for section in d.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3)
        section.right_margin = Cm(3)

    def set_font(style, east_asia, size, bold=None):
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
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
    # 首行缩进2字符
    ind = normal.paragraph_format.element.get_or_add_pPr()
    w_ind = ind.makeelement(qn("w:ind"), {qn("w:firstLineChars"): "200"})
    ind.append(w_ind)

    set_font(styles["Title"], "黑体", 22)
    styles["Title"].paragraph_format.alignment = 1  # 居中

    set_font(styles["Heading 1"], "黑体", 16)
    styles["Heading 1"].paragraph_format.alignment = 1  # 一级标题居中
    styles["Heading 1"].paragraph_format.space_before = Pt(14)
    styles["Heading 1"].paragraph_format.space_after = Pt(10)

    set_font(styles["Heading 2"], "黑体", 14)
    styles["Heading 2"].paragraph_format.space_before = Pt(10)
    styles["Heading 2"].paragraph_format.space_after = Pt(6)

    set_font(styles["Heading 3"], "黑体", 12)
    styles["Heading 3"].paragraph_format.space_before = Pt(8)
    styles["Heading 3"].paragraph_format.space_after = Pt(4)

    set_font(styles["Compact"], "宋体", 10.5)

    d.save(str(REFERENCE))
    return REFERENCE


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
    d = docx.Document(str(out))
    print(f"[build] {out} 生成完成：段落 {len(d.paragraphs)}、表格 {len(d.tables)}、"
          f"参考文档 {reference.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
