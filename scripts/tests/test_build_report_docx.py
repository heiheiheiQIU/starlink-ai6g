import tempfile
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


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

    def test_style_table_applies_header_repeat_margins_and_row_integrity(self):
        document = Document()
        table = document.add_table(rows=2, cols=3)
        table.rows[0].cells[0].text = "字段"
        table.rows[0].cells[1].text = "类型"
        table.rows[0].cells[2].text = "说明"
        MODULE.style_table(table)
        self.assertIn("tblHeader", table.rows[0]._tr.xml)
        self.assertIn("DCE6F1", table.rows[0]._tr.xml)
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


if __name__ == "__main__":
    unittest.main()
