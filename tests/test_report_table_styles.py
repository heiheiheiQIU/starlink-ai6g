import unittest

from docx import Document
from docx.oxml.ns import qn

from scripts.build_report_docx import (
    extract_appendix_table_labels,
    style_appendix_table,
    style_body_table,
)


def table_border(table, edge):
    borders = table._tbl.tblPr.find(qn("w:tblBorders"))
    node = borders.find(qn(f"w:{edge}"))
    return node.get(qn("w:val")), node.get(qn("w:sz")), node.get(qn("w:color"))


def cell_border(cell, edge):
    borders = cell._tc.get_or_add_tcPr().find(qn("w:tcBorders"))
    node = borders.find(qn(f"w:{edge}"))
    return node.get(qn("w:val")), node.get(qn("w:sz")), node.get(qn("w:color"))


class ReportTableStyleTests(unittest.TestCase):
    def test_body_table_uses_black_three_line_style_without_shading(self):
        table = Document().add_table(rows=3, cols=3)
        style_body_table(table)
        self.assertEqual(table_border(table, "top"), ("single", "12", "000000"))
        self.assertEqual(table_border(table, "bottom"), ("single", "12", "000000"))
        for edge in ("left", "right", "insideH", "insideV"):
            self.assertEqual(table_border(table, edge)[0], "nil")
        for cell in table.rows[0].cells:
            self.assertEqual(cell_border(cell, "bottom"), ("single", "6", "000000"))
            shading = cell._tc.get_or_add_tcPr().find(qn("w:shd"))
            self.assertTrue(shading is None or shading.get(qn("w:fill")) in (None, "auto", "FFFFFF"))

    def test_appendix_table_uses_black_full_grid_without_shading(self):
        table = Document().add_table(rows=3, cols=3)
        style_appendix_table(table)
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            self.assertEqual(table_border(table, edge), ("single", "4", "000000"))
        for row in table.rows:
            for cell in row.cells:
                shading = cell._tc.get_or_add_tcPr().find(qn("w:shd"))
                self.assertTrue(shading is None or shading.get(qn("w:fill")) in (None, "auto", "FFFFFF"))

    def test_appendix_labels_are_detected_from_actual_appendix_heading(self):
        source = """
<!-- tab:body | 正文表 -->
|A|B|\n|-|-|\n|1|2|
## 七、附录
这里是目录说明。
## 附录A：数据字典
<!-- tab:observation | 字段表 -->
|A|B|\n|-|-|\n|1|2|
### 附录B：复现
<!-- tab:reproduction | 复现表 -->
|A|B|\n|-|-|\n|1|2|
"""
        self.assertEqual(
            extract_appendix_table_labels(source),
            {"tab:observation", "tab:reproduction"},
        )


if __name__ == "__main__":
    unittest.main()
