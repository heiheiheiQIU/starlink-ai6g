# C Formal-v2 Candidate Readiness Design

## Goal

在不改动正式冻结代码和协议的前提下，提前提供C侧候选输入机器核验入口。B生成180条候选输入后，C可立即得到可审计摘要，但脚本不得自动签署人工回执或授权540次运行。

## Boundaries

- 只读取并调用现有 `backend.formal_freeze.verify_candidate()`。
- 不修改 `backend/`、`training/`、模型、协议、种子或既有回执。
- 检查18个工况、每工况10条、600000—600179种子，以及五类标识/哈希唯一性。
- 输出状态固定为 `machine_verified_human_pending`。
- 输出必须明确 `formal_runs_authorized=false`，人工完成来源、泄漏和三方候选签核前不得启动540次运行。

## Deliverables

- `scripts/review_formal_v2_candidate_c.py`：C侧机器核验与JSON摘要。
- `tests/test_c_formal_candidate_review.py`：结构、唯一性和权限边界测试。
- `docs/handoffs/C_formal_v2_generation_unblock_2026-11-09.md`：向A/B明确C生成前回执已齐及下一步。
