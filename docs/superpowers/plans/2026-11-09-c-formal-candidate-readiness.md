# C Formal-v2 Candidate Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提前完成C侧180条正式候选输入的机器核验入口和生成解阻交接。

**Architecture:** 新脚本复用既有受测 `verify_candidate()`，再生成不含人工签核的C侧摘要。正式冻结代码、模型和预登记协议保持不变。

**Tech Stack:** Python 3.12、pytest、JSON。

**Spec:** `docs/superpowers/specs/2026-11-09-c-formal-candidate-readiness-design.md`

## Global Constraints

- 不修改正式冻结源文件和已签回执。
- 不自动创建 accepted 回执。
- 不授权正式运行。
- 不生成或查看正式策略结果。

## Review Focus

- 重复种子或哈希必须拒绝。
- 非18×10工况矩阵必须拒绝。
- 错误种子范围必须拒绝。
- 机器检查通过不得被表述为人工签核。
- 已存在输出不得覆盖。

---

### Task 1: C候选摘要与权限边界

**Files:** Create `scripts/review_formal_v2_candidate_c.py`; Test `tests/test_c_formal_candidate_review.py`.

- [x] 写失败测试，固定18×10结构、唯一性和 `formal_runs_authorized=false`。
- [x] 运行定向测试确认RED。
- [x] 实现摘要和CLI，复用现有候选验证器。
- [x] 运行定向测试确认GREEN。

### Task 2: 解阻交接与验证

**Files:** Create `docs/handoffs/C_formal_v2_generation_unblock_2026-11-09.md`.

- [x] 记录A/B/C回执位置、同一subject核验和B下一步。
- [x] 运行formal-v2定向回归及全库测试；全库保留既有缺Torch、docx和旧寿命资产错误，不宣称全绿。
- [x] 检查冻结源哈希；确认当前C工作树与已签源码不同，生成必须回到 `48157a8f...`。
- [x] 保存本地里程碑。
