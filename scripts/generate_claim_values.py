"""
claim 唯一事实源生成（材料工程三件套之一）。
从 claims_spec.json 生成 docs/report/claim_values.json：
- pending 条目原样保留（value=null），signed_off 条目带 value/unit/source/hash/scope；
- 禁止手工编辑生成文件；数值变更只改 spec 与证据库。

用法: python scripts/generate_claim_values.py [spec路径] [输出路径]
"""

import json
import sys
from pathlib import Path


def main() -> int:
    spec_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/materials/claims_spec.json")
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("docs/report/claim_values.json")
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    claims = data.get("claims", {})

    payload = {
        "schema_version": "claim-values-v1",
        "generated_from": str(spec_path),
        "claims": claims,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    pending = [key for key, item in claims.items() if item.get("status") != "signed_off"]
    print(f"[claims] 已生成 {out_path}；共 {len(claims)} 条，待签核 {len(pending)} 条：{pending}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
