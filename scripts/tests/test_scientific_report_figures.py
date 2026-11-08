import json
import subprocess
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "figures" / "generated" / "v3" / "report"
GENERATOR = ROOT / "scripts" / "generate_report_figures_v3.mjs"

FIGURES = {
    "C-F03_AI与6G双向耦合_报告版.svg": {
        "required": ["AI价值排序", "6G可行域", "安全解码", "下一决策周期"],
        "forbidden": ["AI决定", "C-F03", "机制与设计图"],
    },
    "A-F02_教师标签质量审计_报告版.svg": {
        "required": ["13/20", "7/20", "19/20", "1/20", "旧20样本冻结包"],
        "forbidden": ["65%", "A-F02", "已签核数据"],
    },
    "B-F02_能量账本校核_报告版.svg": {
        "required": ["0.0200000", "0.0103125", "0.0303125", "Wh", "指定发送段"],
        "forbidden": ["B-F02", "已签核数据", "而不是界面装饰"],
    },
}


class ScientificReportFigureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if GENERATOR.is_file():
            subprocess.run(["node", str(GENERATOR)], cwd=ROOT, check=True)

    def _read_svg(self, name):
        path = OUT / name
        self.assertTrue(path.is_file(), name)
        return path.read_text(encoding="utf-8")

    def test_generator_entrypoint_exists(self):
        self.assertTrue(GENERATOR.is_file(), GENERATOR)

    def test_outputs_use_physical_report_dimensions_and_white_background(self):
        for name in FIGURES:
            text = self._read_svg(name)
            root = ET.fromstring(text)
            self.assertEqual(root.attrib.get("width"), "170mm", name)
            self.assertRegex(root.attrib.get("height", ""), r"^\d+(\.\d+)?mm$")
            first = list(root)[0]
            self.assertTrue(first.tag.endswith("rect"), name)
            self.assertEqual(first.attrib.get("fill"), "#FFFFFF", name)

    def test_outputs_exclude_slide_ui_chrome_and_embedded_titles(self):
        for name, contract in FIGURES.items():
            text = self._read_svg(name)
            self.assertNotIn("<filter", text, name)
            self.assertNotIn("Gradient", text, name)
            self.assertNotIn("linearGradient", text, name)
            self.assertNotIn("radialGradient", text, name)
            self.assertNotIn("drop-shadow", text, name)
            for token in contract["forbidden"]:
                self.assertNotIn(token, text, f"{name}: {token}")

    def test_outputs_preserve_signed_facts_and_boundary_language(self):
        for name, contract in FIGURES.items():
            text = self._read_svg(name)
            for token in contract["required"]:
                self.assertIn(token, text, f"{name}: {token}")

    def test_outputs_use_one_shared_scientific_font_stack(self):
        expected = "Arial, Source Han Sans SC, Microsoft YaHei, sans-serif"
        for name in FIGURES:
            text = self._read_svg(name)
            self.assertIn(expected, text, name)
            self.assertNotIn("Noto Serif", text, name)

    def test_manifest_declares_report_scope_and_svg_as_master(self):
        manifest_path = OUT / "manifest.json"
        self.assertTrue(manifest_path.is_file(), manifest_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["scope"], "report-only")
        self.assertEqual(manifest["master_format"], "SVG")
        self.assertEqual(manifest["background"], "#FFFFFF")
        self.assertEqual(len(manifest["figures"]), 3)
        self.assertEqual(
            {item["file"] for item in manifest["figures"]}, set(FIGURES)
        )


if __name__ == "__main__":
    unittest.main()
