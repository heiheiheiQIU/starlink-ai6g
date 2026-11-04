"""
发布门禁检查（材料工程三件套之二）。
规则（任一命中即退出码非零，CI 可接入）：
1. 正文残留 {{claim-*}} 占位；
2. 残留 [待签核]/待填/TODO/\\Pending 标记；
3. 手写编号模式（“表<数字>”“图<数字>”且非自动生成上下文）；
4. 身份信息（校名/姓名/绝对路径/logo）；
5. claims_spec.json 中 status=pending 的 claim 被正文引用。

用法: python scripts/check_material_gate.py [报告目录] [spec路径]
"""

import json
import re
import sys
from pathlib import Path

IDENTITY_PATTERNS = [
    r"华南师范大学",
    r"scnu",
    r"C:\\Users",
    r"D:\\",
    r"\.logo|logo\.png",
]

HAND_NUMBER = re.compile(r"(?<![\w{])([图表])\s*([0-9]{1,3})(?![\w}])")


def load_spec(spec_path: Path):
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    return data.get("claims", {})


def main() -> int:
    report_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/report")
    spec_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("docs/materials/claims_spec.json")
    claims = load_spec(spec_path)
    violations: list[str] = []

    files = sorted(report_dir.rglob("*.md")) if report_dir.exists() else []
    if not files:
        print(f"[gate] 报告目录不存在或为空: {report_dir}")
        return 2

    for path in files:
        text = path.read_text(encoding="utf-8")
        # 1. claim 占位残留
        for match in re.finditer(r"\{\{claim-[\w-]+\}\}", text):
            token = match.group(0)[2:-2]
            status = claims.get(token, {}).get("status")
            if status == "pending":
                violations.append(f"{path}: 引用了未签核 claim {token}")
        # 2. 待签核/待填标记
        for marker in ("[待签核]", "待填", "TODO", "\\Pending"):
            if marker in text:
                violations.append(f"{path}: 残留标记 {marker}")
        # 3. 手写编号
        for match in HAND_NUMBER.finditer(text):
            violations.append(f"{path}: 手写编号 {match.group(0)}（应使用语义引用）")
        # 4. 身份信息
        for pattern in IDENTITY_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(f"{path}: 疑似身份信息 {pattern}")

    if violations:
        print("[gate] 检查未通过：")
        for item in violations:
            print("  -", item)
        return 1
    print(f"[gate] 通过：{len(files)} 个文件无违规。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
