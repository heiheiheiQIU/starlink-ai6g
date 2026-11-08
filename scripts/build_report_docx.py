"""Build the competition report DOCX with official layout and live references."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import json
import tempfile
from pathlib import Path

import docx
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "docs" / "report"
REFERENCE = REPORT_DIR / "reference_official.docx"

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
V_NS = "urn:schemas-microsoft-com:vml"
EQ_LABEL = re.compile(r"<!--\s*(eq:[\w-]+)\s*-->")
EQ_REF = re.compile(r"式\(?(eq:[\w-]+)\)?")
TAB_LABEL = re.compile(r"<!--\s*(tab:[\w-]+)\s*\|\s*(.*?)\s*-->")
FIG_LABEL = re.compile(r"<!--\s*(fig:[\w-]+)\s*\|\s*(.*?)\s*-->")
CLAIM_TOKEN = re.compile(r"\{\{(claim-[\w-]+)\}\}")


def resolve_pandoc() -> Path:
    candidates: list[Path] = []
    discovered = shutil.which("pandoc")
    if discovered:
        candidates.append(Path(discovered))
    workspace = next((path for path in ROOT.parents if path.name == "Codex-WorkSpace"), None)
    if workspace is not None:
        candidates.append(
            workspace
            / "Biomedical_Engineering"
            / "src"
            / ".deps"
            / "pypandoc"
            / "files"
            / "pandoc.exe"
        )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("未找到可执行的 pandoc；请安装或配置项目内 pypandoc 运行时")


def _set_font(style, east_asia: str, size: float, bold: bool | None = None) -> None:
    style.font.name = "Times New Roman"
    style.font.size = Pt(size)
    style.font.color.rgb = RGBColor(0, 0, 0)
    if bold is not None:
        style.font.bold = bold
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for key, value in (
        ("w:ascii", "Times New Roman"),
        ("w:hAnsi", "Times New Roman"),
        ("w:eastAsia", east_asia),
    ):
        rfonts.set(qn(key), value)


def _set_first_line_chars(style, chars: int) -> None:
    ppr = style.paragraph_format.element.get_or_add_pPr()
    old = ppr.find(qn("w:ind"))
    if old is not None:
        ppr.remove(old)
    indent = OxmlElement("w:ind")
    indent.set(qn("w:firstLineChars"), str(chars * 100))
    ppr.append(indent)


def configure_reference_document(document: docx.Document) -> None:
    """Apply the official A4, margin, font and paragraph rules."""
    for section in document.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(3.0)
        section.header_distance = Cm(1.5)
        section.footer_distance = Cm(1.5)

    styles = document.styles
    normal = styles["Normal"]
    _set_font(normal, "宋体", 12)
    normal.paragraph_format.line_spacing = 1.0
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.widow_control = True
    _set_first_line_chars(normal, 2)

    _set_font(styles["Title"], "黑体", 22, True)
    styles["Title"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    styles["Title"].paragraph_format.space_after = Pt(18)

    heading_rules = (
        ("Heading 1", 16, WD_ALIGN_PARAGRAPH.CENTER, 16, 10),
        ("Heading 2", 14, WD_ALIGN_PARAGRAPH.LEFT, 12, 6),
        ("Heading 3", 12, WD_ALIGN_PARAGRAPH.LEFT, 9, 4),
        ("Heading 4", 12, WD_ALIGN_PARAGRAPH.LEFT, 6, 3),
    )
    for name, size, alignment, before, after in heading_rules:
        style = styles[name]
        _set_font(style, "黑体", size, True)
        style.paragraph_format.alignment = alignment
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.keep_together = True
        _set_first_line_chars(style, 0)

    for name in ("Compact", "Caption"):
        if name in [style.name for style in styles]:
            _set_font(styles[name], "宋体", 10.5)
            styles[name].font.italic = False
            styles[name].font.bold = False
            styles[name].paragraph_format.line_spacing = 1.0
            styles[name].paragraph_format.space_after = Pt(3)
            _set_first_line_chars(styles[name], 0)

    if "Table" in [style.name for style in styles]:
        _set_font(styles["Table"], "宋体", 9.5)
        styles["Table"].paragraph_format.line_spacing = 1.0
        _set_first_line_chars(styles["Table"], 0)


def ensure_reference_doc() -> Path:
    if REFERENCE.exists():
        return REFERENCE
    raw = subprocess.run(
        [str(resolve_pandoc()), "--print-default-data-file", "reference.docx"],
        capture_output=True,
        check=False,
    )
    if raw.returncode != 0:
        raise RuntimeError(f"无法生成参考文档: {raw.stderr.decode(errors='ignore')}")
    REFERENCE.write_bytes(raw.stdout)
    document = docx.Document(str(REFERENCE))
    configure_reference_document(document)
    document.save(str(REFERENCE))
    return REFERENCE


def _append_child(parent, name: str, **attrs):
    child = OxmlElement(name)
    for key, value in attrs.items():
        child.set(qn(key), str(value))
    parent.append(child)
    return child


def _set_table_border(table, edge: str, value: str, size: int, color: str) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    element = borders.find(qn(f"w:{edge}"))
    if element is None:
        element = OxmlElement(f"w:{edge}")
        borders.append(element)
    element.set(qn("w:val"), value)
    element.set(qn("w:sz"), str(size))
    element.set(qn("w:color"), color)


def _set_cell_border(cell, edge: str, value: str, size: int, color: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    element = borders.find(qn(f"w:{edge}"))
    if element is None:
        element = OxmlElement(f"w:{edge}")
        borders.append(element)
    element.set(qn("w:val"), value)
    element.set(qn("w:sz"), str(size))
    element.set(qn("w:color"), color)


def _clear_cell_decoration(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is not None:
        tc_pr.remove(shading)
    borders = tc_pr.find(qn("w:tcBorders"))
    if borders is not None:
        tc_pr.remove(borders)


def _style_table_layout(table) -> None:
    """Apply shared typography, widths and spacing without choosing border semantics."""
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    column_count = len(table.columns)
    presets = {
        2: [4.2, 10.8],
        3: [3.2, 3.0, 8.8],
        4: [2.6, 4.4, 3.0, 5.0],
        5: [2.1, 3.2, 3.1, 2.5, 4.1],
        6: [2.0, 2.4, 2.5, 2.5, 2.5, 3.1],
    }
    widths = presets.get(column_count, [15.0 / max(column_count, 1)] * column_count)

    for row_index, row in enumerate(table.rows):
        tr_pr = row._tr.get_or_add_trPr()
        if tr_pr.find(qn("w:cantSplit")) is None:
            _append_child(tr_pr, "w:cantSplit")
        if row_index == 0 and tr_pr.find(qn("w:tblHeader")) is None:
            _append_child(tr_pr, "w:tblHeader", **{"w:val": "true"})
        for column_index, cell in enumerate(row.cells):
            _clear_cell_decoration(cell)
            cell.width = Cm(widths[min(column_index, len(widths) - 1)])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_mar = tc_pr.find(qn("w:tcMar"))
            if tc_mar is None:
                tc_mar = OxmlElement("w:tcMar")
                tc_pr.append(tc_mar)
            for side, value in (("top", 70), ("bottom", 70), ("left", 100), ("right", 100)):
                node = tc_mar.find(qn(f"w:{side}"))
                if node is None:
                    node = OxmlElement(f"w:{side}")
                    tc_mar.append(node)
                node.set(qn("w:w"), str(value))
                node.set(qn("w:type"), "dxa")
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.first_line_indent = None
                paragraph.paragraph_format.space_before = Pt(0)
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.0
                if row_index == 0:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(9.5)
                    run.font.bold = row_index == 0
                    rpr = run._r.get_or_add_rPr()
                    rfonts = rpr.find(qn("w:rFonts"))
                    if rfonts is None:
                        rfonts = OxmlElement("w:rFonts")
                        rpr.append(rfonts)
                    rfonts.set(qn("w:eastAsia"), "宋体" if row_index else "黑体")


def style_body_table(table) -> None:
    """Use a publication-style black three-line table for report body content."""
    _style_table_layout(table)
    _set_table_border(table, "top", "single", 12, "000000")
    _set_table_border(table, "bottom", "single", 12, "000000")
    for edge in ("left", "right", "insideH", "insideV"):
        _set_table_border(table, edge, "nil", 0, "000000")
    for cell in table.rows[0].cells:
        _set_cell_border(cell, "bottom", "single", 6, "000000")


def style_appendix_table(table) -> None:
    """Use an unshaded black-and-white full grid for appendix dictionaries and indexes."""
    _style_table_layout(table)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        _set_table_border(table, edge, "single", 4, "000000")


def style_table(table, *, appendix: bool = False) -> None:
    """Backward-compatible table dispatcher."""
    if appendix:
        style_appendix_table(table)
    else:
        style_body_table(table)


def compact_appendix_table(table) -> None:
    """Tighten evidence-index tables so short trailing rows do not create an orphan page."""
    for row in table.rows:
        for cell in row.cells:
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_mar = tc_pr.find(qn("w:tcMar"))
            if tc_mar is not None:
                for side in ("top", "bottom"):
                    node = tc_mar.find(qn(f"w:{side}"))
                    if node is not None:
                        node.set(qn("w:w"), "35")
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.line_spacing = 0.9
                for run in paragraph.runs:
                    run.font.size = Pt(8.5)


def extract_equation_labels(source: Path) -> list[str]:
    return EQ_LABEL.findall(source.read_text(encoding="utf-8"))


def extract_table_labels(source: Path) -> list[tuple[str, str]]:
    return TAB_LABEL.findall(source.read_text(encoding="utf-8"))


def extract_appendix_table_labels(source_text: str) -> set[str]:
    """Return table labels located under a real appendix heading such as 附录A/附录B."""
    appendix = re.search(r"^#{2,4}\s+附录[A-Z0-9]", source_text, re.MULTILINE)
    if appendix is None:
        return set()
    return {label for label, _title in TAB_LABEL.findall(source_text[appendix.start():])}


def extract_figure_labels(source: Path) -> list[tuple[str, str]]:
    return FIG_LABEL.findall(source.read_text(encoding="utf-8"))


def render_claim_tokens(text: str, claims: dict) -> str:
    def replace(match: re.Match[str]) -> str:
        claim_id = match.group(1)
        item = claims.get(claim_id)
        if item is None:
            raise ValueError(f"未知主张: {claim_id}")
        if item.get("status") != "signed_off":
            raise ValueError(f"未签核主张不得进入发布稿: {claim_id}")
        return f"〔{claim_id.removeprefix('claim-')}〕"

    return CLAIM_TOKEN.sub(replace, text)


def _bookmark_name(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", label)


def _append_field(paragraph, instruction: str, fallback: str = "0") -> None:
    begin = paragraph.add_run()._r
    _append_child(begin, "w:fldChar", **{"w:fldCharType": "begin"})
    instr = paragraph.add_run()._r
    instruction_text = _append_child(instr, "w:instrText", **{"xml:space": "preserve"})
    instruction_text.text = f" {instruction} "
    separate = paragraph.add_run()._r
    _append_child(separate, "w:fldChar", **{"w:fldCharType": "separate"})
    paragraph.add_run(fallback)
    end = paragraph.add_run()._r
    _append_child(end, "w:fldChar", **{"w:fldCharType": "end"})


def add_equation_number(paragraph, number: int, label: str) -> str:
    """Append a live SEQ field and bookmark to a display equation."""
    bookmark = _bookmark_name(label)
    paragraph.paragraph_format.first_line_indent = None
    paragraph.paragraph_format.tab_stops.clear_all()
    paragraph.paragraph_format.tab_stops.add_tab_stop(Cm(7.5), WD_TAB_ALIGNMENT.CENTER)
    paragraph.paragraph_format.tab_stops.add_tab_stop(Cm(15), WD_TAB_ALIGNMENT.RIGHT)

    first_content = next((node for node in paragraph._p if node.tag != qn("w:pPr")), None)
    tab_run = OxmlElement("w:r")
    _append_child(tab_run, "w:tab")
    if first_content is not None:
        first_content.addprevious(tab_run)
    else:
        paragraph._p.append(tab_run)

    paragraph.add_run("\t（")
    bookmark_start = OxmlElement("w:bookmarkStart")
    bookmark_start.set(qn("w:id"), str(1000 + number))
    bookmark_start.set(qn("w:name"), bookmark)
    paragraph._p.append(bookmark_start)
    _append_field(paragraph, "SEQ Equation \\* ARABIC", str(number))
    bookmark_end = OxmlElement("w:bookmarkEnd")
    bookmark_end.set(qn("w:id"), str(1000 + number))
    paragraph._p.append(bookmark_end)
    paragraph.add_run("）")
    return bookmark


def add_table_caption(table, number: int, label: str, title: str) -> str:
    bookmark = _bookmark_name(label)
    xml_paragraph = OxmlElement("w:p")
    table._tbl.addprevious(xml_paragraph)
    paragraph = Paragraph(xml_paragraph, table._parent)
    paragraph.style = "Caption"
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = True
    paragraph.add_run("表 ")
    bookmark_start = OxmlElement("w:bookmarkStart")
    bookmark_start.set(qn("w:id"), str(2000 + number))
    bookmark_start.set(qn("w:name"), bookmark)
    paragraph._p.append(bookmark_start)
    _append_field(paragraph, "SEQ Table \\* ARABIC", str(number))
    bookmark_end = OxmlElement("w:bookmarkEnd")
    bookmark_end.set(qn("w:id"), str(2000 + number))
    paragraph._p.append(bookmark_end)
    paragraph.add_run(f"  {title}")
    return bookmark


def add_figure_caption(image_paragraph, number: int, label: str, title: str) -> str:
    """Insert a live figure caption immediately after an image paragraph."""
    bookmark = _bookmark_name(label)
    xml_paragraph = OxmlElement("w:p")
    image_paragraph._p.addnext(xml_paragraph)
    paragraph = Paragraph(xml_paragraph, image_paragraph._parent)
    paragraph.style = "Caption"
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = False
    paragraph.add_run("图 ")
    bookmark_start = OxmlElement("w:bookmarkStart")
    bookmark_start.set(qn("w:id"), str(3000 + number))
    bookmark_start.set(qn("w:name"), bookmark)
    paragraph._p.append(bookmark_start)
    _append_field(paragraph, "SEQ Figure \\* ARABIC", str(number))
    bookmark_end = OxmlElement("w:bookmarkEnd")
    bookmark_end.set(qn("w:id"), str(3000 + number))
    paragraph._p.append(bookmark_end)
    paragraph.add_run(f"  {title}")
    return bookmark


def _all_paragraphs(document):
    for paragraph in document.paragraphs:
        yield paragraph
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from cell.paragraphs


def replace_semantic_references(
    document,
    bookmark_map: dict[str, str],
    table_bookmark_map: dict[str, str] | None = None,
    figure_bookmark_map: dict[str, str] | None = None,
) -> None:
    """Replace equation/table/figure source tokens with Word REF fields."""
    table_bookmark_map = table_bookmark_map or {}
    figure_bookmark_map = figure_bookmark_map or {}
    combined = re.compile(
        r"式\(?(eq:[\w-]+)\)?|表\(?(tab:[\w-]+)\)?|图\(?(fig:[\w-]+)\)?"
    )
    for paragraph in list(_all_paragraphs(document)):
        original = paragraph.text
        matches = list(combined.finditer(original))
        if not matches:
            continue
        ppr = paragraph._p.pPr
        for child in list(paragraph._p):
            if child is not ppr:
                paragraph._p.remove(child)
        cursor = 0
        for match in matches:
            paragraph.add_run(original[cursor:match.start()])
            equation_label, table_label, figure_label = match.groups()
            if equation_label:
                paragraph.add_run("式（")
                _append_field(
                    paragraph,
                    f"REF {bookmark_map.get(equation_label, _bookmark_name(equation_label))} \\h",
                    "?",
                )
                paragraph.add_run("）")
            elif table_label:
                paragraph.add_run("表")
                _append_field(
                    paragraph,
                    f"REF {table_bookmark_map.get(table_label, _bookmark_name(table_label))} \\h",
                    "?",
                )
            else:
                paragraph.add_run("图")
                _append_field(
                    paragraph,
                    f"REF {figure_bookmark_map.get(figure_label, _bookmark_name(figure_label))} \\h",
                    "?",
                )
            cursor = match.end()
        paragraph.add_run(original[cursor:])


def _add_page_numbers(document) -> None:
    for section in document.sections:
        paragraph = section.footer.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.clear()
        _append_field(paragraph, "PAGE", "1")


def _request_field_update(document) -> None:
    settings = document.settings.element
    update = settings.find(qn("w:updateFields"))
    if update is None:
        update = OxmlElement("w:updateFields")
        settings.append(update)
    update.set(qn("w:val"), "true")


def postprocess(out: Path, source: Path) -> None:
    document = docx.Document(str(out))
    configure_reference_document(document)
    table_labels = extract_table_labels(source)
    appendix_table_labels = extract_appendix_table_labels(source.read_text(encoding="utf-8"))
    table_bookmark_map: dict[str, str] = {}
    for index, table in enumerate(document.tables, start=1):
        if index <= len(table_labels):
            label, title = table_labels[index - 1]
        else:
            label, title = f"tab:auto-{index}", "数据表"
        style_table(table, appendix=label in appendix_table_labels)
        if label in {"tab:claims", "tab:reproduction"}:
            compact_appendix_table(table)
        table_bookmark_map[label] = add_table_caption(table, index, label, title)

    labels = extract_equation_labels(source)
    w_ns = {"w": W_NS, "m": M_NS}
    equations = [
        paragraph
        for paragraph in document.paragraphs
        if paragraph._p.findall(".//m:oMathPara", w_ns)
        or (
            paragraph._p.findall(".//m:oMath", w_ns)
            and not "".join(paragraph._p.itertext()).strip()
        )
    ]
    bookmark_map: dict[str, str] = {}
    for index, paragraph in enumerate(equations, start=1):
        label = labels[index - 1] if index <= len(labels) else f"eq:auto-{index}"
        bookmark_map[label] = add_equation_number(paragraph, index, label)
    figure_labels = extract_figure_labels(source)
    image_paragraphs = [
        paragraph
        for paragraph in document.paragraphs
        if paragraph._p.findall(".//w:drawing", {"w": W_NS})
        or paragraph._p.findall(".//v:imagedata", {"v": V_NS})
    ]
    figure_bookmark_map: dict[str, str] = {}
    for index, paragraph in enumerate(image_paragraphs, start=1):
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.first_line_indent = None
        paragraph.paragraph_format.keep_with_next = True
        if index <= len(figure_labels):
            label, title = figure_labels[index - 1]
        else:
            label, title = f"fig:auto-{index}", "系统图"
        figure_bookmark_map[label] = add_figure_caption(
            paragraph, index, label, title
        )
    replace_semantic_references(
        document,
        bookmark_map,
        table_bookmark_map,
        figure_bookmark_map,
    )

    in_references = False
    for paragraph in document.paragraphs:
        if paragraph.style and paragraph.style.name == "Heading 1":
            in_references = paragraph.text.strip() == "参考文献"
        if in_references and paragraph.style.name == "Normal" and paragraph.text.strip():
            paragraph.paragraph_format.left_indent = Cm(0.74)
            paragraph.paragraph_format.first_line_indent = Cm(-0.74)
            paragraph.paragraph_format.line_spacing = 1.15
            paragraph.paragraph_format.space_after = Pt(3)
            for run in paragraph.runs:
                run.font.size = Pt(10.5)

    _add_page_numbers(document)
    _request_field_update(document)
    document.save(str(out))
    print(
        f"[build] {out}：段落 {len(document.paragraphs)}、表格 {len(document.tables)}、"
        f"公式 {len(equations)}、图 {len(image_paragraphs)}、"
        f"公式标签 {len(labels)}、图标签 {len(figure_labels)}"
    )


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else REPORT_DIR / "report_v2.md"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else REPORT_DIR / "星地智调_作品方案_v2.docx"
    reference = ensure_reference_doc()
    claims_path = ROOT / "docs" / "materials" / "claims_spec.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8")).get("claims", {})
    rendered_text = render_claim_tokens(source.read_text(encoding="utf-8"), claims)
    with tempfile.TemporaryDirectory(prefix="xingdi-report-") as directory:
        rendered_source = Path(directory) / source.name
        rendered_source.write_text(rendered_text, encoding="utf-8")
        result = subprocess.run(
            [
                str(resolve_pandoc()),
                str(rendered_source),
                "--resource-path",
                str(ROOT),
                "--reference-doc",
                str(reference),
                "-o",
                str(out),
            ],
            capture_output=True,
            check=False,
        )
    if result.returncode != 0:
        print(result.stderr.decode(errors="ignore"))
        return 1
    postprocess(out, source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
