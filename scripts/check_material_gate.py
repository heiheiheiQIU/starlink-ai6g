"""
发布门禁检查 v2（材料工程三件套）。
规则（任一命中即退出码非零，CI 可接入）：
1. 正文残留 {{claim-*}} 占位；引用了 status=pending 的 claim；
2. 引用 unknown claim（spec 中不存在）；
3. 残留 [待签核]/待填/TODO/\\Pending；
4. 手写编号（"表<数字>""图<数字>"，含"见表3""如图4"）；
5. 身份信息（校名/姓名/绝对路径/logo/指导教师）；
6. 禁用措辞（显著优于/明显提升/大幅改善/最优方案/业界领先等——报告全文禁用）。

用法: python scripts/check_material_gate.py [报告目录] [spec路径] [--selftest]
"""

import json
import re
import sys
import tempfile
from pathlib import Path

IDENTITY_PATTERNS = [
    r"华南师范大学",
    r"scnu",
    r"指导教师",
    r"C:\\Users",
    r"[A-Za-z]:\\",
    r"\.logo|logo\.png",
]

FORBIDDEN_WORDS = [
    "显著优于",
    "明显提升",
    "大幅改善",
    "领先",
    "最优方案",
    "业界领先",
]

HAND_NUMBER = re.compile(r"[图表]\s*[0-9]{1,3}")
CLAIM_TOKEN = re.compile(r"\{\{(claim-[\w-]+)\}\}")


def load_spec(spec_path: Path):
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    return data.get("claims", {})


def scan_text(path: Path, text: str, claims: dict) -> list[str]:
    violations: list[str] = []
    # 1/2. claim 占位与状态
    for match in CLAIM_TOKEN.finditer(text):
        token = match.group(1)
        if token not in claims:
            violations.append(f"{path}: 引用了未知 claim {token}")
            continue
        if claims[token].get("status") != "signed_off":
            violations.append(f"{path}: 引用了未签核 claim {token}")
    # 3. 残留标记
    for marker in ("[待签核]", "待填", "TODO", "\\Pending"):
        if marker in text:
            violations.append(f"{path}: 残留标记 {marker}")
    # 4. 手写编号（含"见表3""如图4"）
    for match in HAND_NUMBER.finditer(text):
        violations.append(f"{path}: 手写编号 {match.group(0)}（应使用语义引用）")
    # 5. 身份信息
    for pattern in IDENTITY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(f"{path}: 疑似身份信息 {pattern}")
    # 6. 禁用措辞
    for word in FORBIDDEN_WORDS:
        if word in text:
            violations.append(f"{path}: 禁用措辞「{word}」（四档口径外不得使用）")
    return violations


def run(report_dir: Path, spec_path: Path) -> int:
    claims = load_spec(spec_path)
    files = sorted(report_dir.rglob("*.md")) if report_dir.exists() else []
    if not files:
        print(f"[gate] 报告目录不存在或为空: {report_dir}")
        return 2
    violations: list[str] = []
    for path in files:
        violations.extend(scan_text(path, path.read_text(encoding="utf-8"), claims))
    if violations:
        print("[gate] 检查未通过：")
        for item in violations:
            print("  -", item)
        return 1
    print(f"[gate] 通过：{len(files)} 个文件无违规。")
    return 0


def selftest() -> int:
    # 沙箱下由python创建的目录ACL异常，自测目录改由外部（pwsh）预创建并通过环境变量传入
    import os

    base = Path(os.environ.get("GATE_SELFTEST_BASE", "gate_selftest_tmp"))
    clean_dir = base / "clean"
    dirty_dir = base / "dirty"
    spec = base / "spec.json"
    try:
        spec.write_text(
            json.dumps(
                {
                    "claims": {
                        "claim-X1": {"status": "pending"},
                        "claim-E1": {"status": "signed_off"},
                    }
                }
            ),
            encoding="utf-8",
        )
        (clean_dir / "clean.md").write_text(
            "结论见式(eq:wot)。数据 {{claim-E1}} 已签核。", encoding="utf-8"
        )
        (dirty_dir / "dirty.md").write_text(
            "learned 显著优于规则，见表3，华南师范大学，{{claim-X1}}，{{claim-unknown}}。TODO",
            encoding="utf-8",
        )
        rc_clean = run(clean_dir, spec)
        rc_dirty = run(dirty_dir, spec)
        ok = rc_clean == 0 and rc_dirty != 0
        print(f"[selftest] clean={rc_clean} dirty={rc_dirty} -> {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        for path in (clean_dir / "clean.md", dirty_dir / "dirty.md", spec):
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    report_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/report")
    spec_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("docs/materials/claims_spec.json")
    raise SystemExit(run(report_dir, spec_path))
