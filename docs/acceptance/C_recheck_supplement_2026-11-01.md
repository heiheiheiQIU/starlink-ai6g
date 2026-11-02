# C 严格复查补充注记（2026-11-01 晚）

对近三轮审计结论的逐项重核（重查源码/远端，非复述）结果与两点增量，存档如下。

## 一、重核结果（全部成立）

1. B 对 PR #8 的 BadZipFile 发现：通读 `learned.py@11c00374` 全文确认——`_load_bundle` except 元组为 `(OSError, ValueError, TypeError)`，真坏ZIP抛 `zipfile.BadZipFile` 原样泄漏；且**全文件其余异常面已逐一核对**：名字集合检查位于数组访问之前（无KeyError泄漏）、NaN守卫覆盖权重/归一化/输出三层、config/hash/JSON各路径受控——除该缺口外无其他泄漏点。
2. A 应用 B 补丁的 `3ea06f6` 与 B 最小补丁逐行一致（三 hunk 无夹带）；`B_API_lock_A_2026-11-01.md` 回执在 11c00374 上。
3. **R2/R5 两份回执在 origin/feature/ai 仍缺失**（A 未推送，本地分支 codex/a-r2-r5-receipts）。
4. B 的坏ZIP回归测试构造严谨（真PK签名+损坏载荷+按实际SHA绕过哈希门+断言MODEL_FORMAT）。
5. B 的 46定向/501全库数字与消息、回执交叉一致。

## 二、两点增量

1. **EOFError 同类缺口（C 补充建议）**：截断的 npz 会抛 `zipfile.BadZipFile` 或 `EOFError`，后者同样不在当前 except 元组——A 修订时应把 `BadZipFile` 与 `EOFError` 一并纳入 `MODEL_FORMAT` 转换，并补"截断文件"回归一条；
2. **前端聚光灯已知边界（C 自查披露）**：演示中目标元素被完全滚出视口时，clip-path 洞退化为零尺寸 → 蒙层变全屏暗幕（无高亮但旁白仍在）。行为可接受，记录在案；若后续视觉验收反馈不佳，方案=洞退化时保留上一有效路径。
