import tempfile
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from lxml import etree


SCRIPT = Path(__file__).resolve().parents[1] / "build_report_docx.py"
SPEC = spec_from_file_location("build_report_docx", SCRIPT)
MODULE = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ReportBuilderTests(unittest.TestCase):
    def test_configure_reference_document_sets_a4_and_official_body_style(self):
        document = Document()
        MODULE.configure_reference_document(document)
        section = document.sections[0]
        self.assertEqual(round(section.page_width.cm, 1), 21.0)
        self.assertEqual(round(section.page_height.cm, 1), 29.7)
        self.assertEqual(round(section.top_margin.cm, 1), 2.5)
        self.assertEqual(round(section.left_margin.cm, 1), 3.0)
        normal = document.styles["Normal"]
        self.assertEqual(normal.font.size.pt, 12)
        self.assertEqual(normal.paragraph_format.line_spacing, 1.0)
        self.assertEqual(normal.element.rPr.rFonts.get(qn("w:eastAsia")), "宋体")

    def test_style_table_applies_three_line_rules_header_repeat_and_row_integrity(self):
        document = Document()
        table = document.add_table(rows=2, cols=3)
        table.rows[0].cells[0].text = "字段"
        table.rows[0].cells[1].text = "类型"
        table.rows[0].cells[2].text = "说明"
        MODULE.style_table(table)
        self.assertIn("tblHeader", table.rows[0]._tr.xml)
        self.assertNotIn("w:shd", table.rows[0]._tr.xml)
        self.assertIn('w:top w:val="single" w:sz="12" w:color="000000"', table._tbl.xml)
        self.assertIn('w:bottom w:val="single" w:sz="12" w:color="000000"', table._tbl.xml)
        self.assertIn('w:bottom w:val="single" w:sz="6" w:color="000000"', table.rows[0]._tr.xml)
        self.assertTrue(all("cantSplit" in row._tr.xml for row in table.rows))
        self.assertTrue(all("tcMar" in cell._tc.xml for row in table.rows for cell in row.cells))

    def test_equation_numbering_uses_seq_bookmark_and_ref_field(self):
        document = Document()
        equation = document.add_paragraph()
        equation.add_run("x+y")
        reference = document.add_paragraph("由式(eq:wot)可得。")
        MODULE.add_equation_number(equation, 1, "eq:wot")
        MODULE.replace_semantic_references(document, {"eq:wot": "eq_wot"})
        self.assertIn("SEQ Equation", equation._p.xml)
        self.assertIn("bookmarkStart", equation._p.xml)
        self.assertIn('w:name="eq_wot"', equation._p.xml)
        self.assertNotIn("式(eq:wot)", reference.text)
        self.assertIn("REF eq_wot", reference._p.xml)

    def test_extract_equation_labels_preserves_source_order(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "report.md"
            source.write_text(
                "<!-- eq:first -->\n$$ a=1 $$\n\n<!-- eq:second -->\n$$ b=2 $$\n",
                encoding="utf-8",
            )
            self.assertEqual(MODULE.extract_equation_labels(source), ["eq:first", "eq:second"])

    def test_resolve_pandoc_returns_an_executable_file(self):
        pandoc = MODULE.resolve_pandoc()
        self.assertTrue(pandoc.is_file())
        self.assertEqual(pandoc.name.lower(), "pandoc.exe")

    def test_render_claim_tokens_uses_evidence_tags_and_rejects_pending(self):
        claims = {
            "claim-E1": {"status": "signed_off"},
            "claim-X1": {"status": "pending"},
        }
        self.assertEqual(MODULE.render_claim_tokens("值{{claim-E1}}", claims), "值〔E1〕")
        with self.assertRaises(ValueError):
            MODULE.render_claim_tokens("值{{claim-X1}}", claims)

    def test_table_caption_uses_seq_bookmark_and_reference(self):
        document = Document()
        table = document.add_table(rows=2, cols=2)
        reference = document.add_paragraph("详见表(tab:kpi)。")
        bookmark = MODULE.add_table_caption(table, 1, "tab:kpi", "关键KPI与度量来源")
        MODULE.replace_semantic_references(document, {}, {"tab:kpi": bookmark})
        previous = table._tbl.getprevious().xml
        self.assertIn("SEQ Table", previous)
        self.assertIn('w:name="tab_kpi"', previous)
        self.assertNotIn("表(tab:kpi)", reference.text)
        self.assertIn("REF tab_kpi", reference._p.xml)

    def test_extract_figure_labels_preserves_title_and_source_order(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "report.md"
            source.write_text(
                "<!-- fig:flow | 端到端闭环 -->\n![](flow.svg){width=15cm}\n\n"
                "<!-- fig:evidence | 证据链 -->\n![](evidence.svg){width=15cm}\n",
                encoding="utf-8",
            )
            self.assertEqual(
                MODULE.extract_figure_labels(source),
                [("fig:flow", "端到端闭环"), ("fig:evidence", "证据链")],
            )

    def test_figure_caption_uses_seq_bookmark_and_reference(self):
        document = Document()
        image_paragraph = document.add_paragraph("图像占位")
        reference = document.add_paragraph("系统闭环如图(fig:flow)所示。")
        bookmark = MODULE.add_figure_caption(
            image_paragraph, 1, "fig:flow", "端到端闭环"
        )
        MODULE.replace_semantic_references(
            document,
            {},
            {},
            {"fig:flow": bookmark},
        )
        following = image_paragraph._p.getnext().xml
        self.assertIn("SEQ Figure", following)
        self.assertIn('w:name="fig_flow"', following)
        self.assertNotIn("图(fig:flow)", reference.text)
        self.assertIn("REF fig_flow", reference._p.xml)

    def test_v3_report_has_twelve_bound_figures_and_current_formal_status(self):
        source = MODULE.REPORT_DIR / "report_v3.md"
        text = source.read_text(encoding="utf-8")
        figures = MODULE.extract_figure_labels(source)
        self.assertEqual(len(figures), 12)
        self.assertEqual(len({label for label, _ in figures}), 12)
        self.assertIn("540/540", text)
        self.assertIn("46.54%", text)
        self.assertIn("51.15%", text)
        self.assertIn("2160", text)
        self.assertIn("技术结果已完成", text)
        self.assertNotIn("当前可计入材料的输入仍为0条", text)
        self.assertNotIn("正式策略运行仍为0次", text)
        self.assertNotIn("换机验收尚待完成", text)
        self.assertIn("恢复性数据试验没有达到训练条件", text)
        self.assertNotIn("后端570项", text)
        self.assertNotIn("前端71项", text)
        self.assertNotIn("可在干净环境按清单完整复现", text)

    def test_horizontal_rule_is_not_counted_as_a_figure(self):
        document = Document()
        paragraph = document.add_paragraph()
        pict = MODULE.OxmlElement("w:pict")
        etree.SubElement(pict, f"{{{MODULE.V_NS}}}rect")
        paragraph.add_run()._r.append(pict)
        self.assertFalse(paragraph._p.findall(".//v:imagedata", {"v": MODULE.V_NS}))


if __name__ == "__main__":
    unittest.main()
