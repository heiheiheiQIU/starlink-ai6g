# C Sandbox Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 审计并集成B的sandbox场景构造、真实事件和离线包，在现有工程控制台中交付可编辑参数、真实运行、按策略回放、结果与证据导出。

**Architecture:** 服务端 `compile_sandbox_axes` 是场景生成唯一权威源；前端只提交十类受控参数，不生成任务、窗口或HealthEstimate。全站继续复用唯一RunContext，sandbox与formal保持目录、run_id和结论口径隔离。

**Tech Stack:** Python 3.12、FastAPI、Pydantic、React 18、TypeScript、Vitest、Vite。

**Spec:** `docs/team/ABC_最终冲刺与交互仿真实施方案_2026-11-08.md`

## Global Constraints

- 不生成、筛选或美化AI收益；Learned为idle和0交付必须原样显示。
- formal_v2候选生成、冻结和540次运行继续受A/B/C两阶段签核约束。
- 前端不得复制 `compile_sandbox_axes` 的任务、窗口、健康或协议构造规则。
- sandbox只标记为合成交互实验，不进入claim。
- 修改参数只创建新run，不修改已完成run的证据。
- 用户删除的报告PDF和Word临时锁文件不得纳入提交。

## Review Focus

- 非法seed、超范围reserve和合同外枚举必须在前端阻止或由后端422明确拒绝，不能静默修正。
- 多策略事件必须先按policy_id分流再按sim_time_s回放，不能把两条策略时间轴串成一条业务轨迹。
- running期间分页追加事件不得重复，completed后必须最后排空。
- 参数变更后旧run必须明确标为历史，不得把旧结果挂到新配置。
- 后端离线包、远程提交和本地证据的SHA/版本边界必须可追溯。

---

### Task 1: Audit and integrate B delivery

**Files:**
- Merge: `origin/codex/b-sandbox-delivery-20261109`
- Verify: `backend/sandbox.py`, `backend/api/service.py`, `tests/test_sandbox.py`
- Place locally: `runs/B_sandbox_offline_20261109/`

**Interfaces:**
- Consumes: B branch `c43978c`, offline manifest and golden runs.
- Produces: integrated backend and evidence tree without replacing later C frontend files.

- [ ] Verify branch SHA, all offline member hashes, clean offline import and five golden runs.
- [ ] Merge B branch and resolve conflicts by preserving the latest C frontend while accepting B backend/contracts/evidence.
- [ ] Run B sandbox/backend regression tests and record exact result.
- [ ] Commit the integration merge.

### Task 2: Close the generation-precheck handoff gap

**Files:**
- Create: `docs/evidence/B/sprint_2026-11-09/generation/C.json`
- Modify: `docs/evidence/B/sprint_2026-11-09/generation/status.json`
- Create: `docs/acceptance/B_sandbox_C_review_2026-11-09.md`

**Interfaces:**
- Consumes: `docs/acceptance/B_formal_v2_generation_C_2026-11-08.json` and B subject.
- Produces: original C receipt discoverable by B; audit verdict that does not authorize candidate freeze or formal runs.

- [ ] Add tests/checks that A/B/C pre-generation receipts bind the identical subject.
- [ ] Copy C's signed machine-readable receipt byte-for-byte and update status to `ready_for_candidate_generation`.
- [ ] Write the C sandbox audit with evidence, accepted boundaries and retained negative results.
- [ ] Verify hashes and commit.

### Task 3: Add typed sandbox request construction

**Files:**
- Create: `frontend/src/domain/sandbox.ts`
- Test: `frontend/src/domain/sandbox.test.ts`

**Interfaces:**
- Consumes: `sandbox_scenario_edit_v1` values.
- Produces: `makeSandboxRunRequest(axes, policies, seed): RunRequest` and validation result; no ScenarioConfig construction.

- [ ] Write failing tests for golden S1 request, invalid seed, reserve and enum boundaries.
- [ ] Run tests and confirm RED.
- [ ] Implement only axis validation and request serialization.
- [ ] Run tests and confirm GREEN; commit.

### Task 4: Build and integrate the sandbox control panel

**Files:**
- Create: `frontend/src/components/SandboxControlPanel.tsx`
- Test: `frontend/src/components/SandboxControlPanel.test.tsx`
- Modify: `frontend/src/pages/MatrixPage.tsx`, `frontend/src/pages/MatrixPage.test.tsx`, `frontend/src/styles/global.css`

**Interfaces:**
- Consumes: Task 3 request builder and shared RunController.
- Produces: P0 axis controls, summary, real POST, stale-result boundary, status/results/export.

- [ ] Write failing UI tests for request payload, invalid input no-POST, stale state, backend error and Learned idle/zero display.
- [ ] Run tests and confirm RED.
- [ ] Implement panel and embed it above the historical 18-cell development matrix.
- [ ] Run component/page tests and confirm GREEN; commit.

### Task 5: Make replay policy-aware

**Files:**
- Modify: `frontend/src/components/EventStreamCard.tsx`
- Test: `frontend/src/components/EventStreamCard.test.tsx`
- Modify: `frontend/src/pages/FlowWorkspace.tsx`, `frontend/src/domain/liveRunSession.ts`

**Interfaces:**
- Consumes: B event contract where policy batches restart `sim_time_s` at zero.
- Produces: explicit active-policy replay and policy-specific mission-stage projection.

- [ ] Write failing tests showing EDF and Learned events are not combined into one replay timeline.
- [ ] Run tests and confirm RED.
- [ ] Add policy selection and filter mission projection to the active backend policy.
- [ ] Run tests and confirm GREEN; commit.

### Task 6: End-to-end verification and release handoff

**Files:**
- Modify: `docs/audits/C_milestone_big_check_2026-11-09.md`
- Create: `docs/handoffs/C_sandbox_integration_2026-11-09.md`

**Interfaces:**
- Consumes: merged backend, C frontend, B offline evidence.
- Produces: tested integration and exact next actions for A/B/C.

- [ ] Run full frontend tests, TypeScript, production build, B backend regression and a fresh five-scene HTTP verification.
- [ ] Start integrated backend and exercise a sandbox request, event pagination, results and ZIP export.
- [ ] Review the whole diff, record any rulings/minors, and ensure no formal claim changed.
- [ ] Commit, push `feature/frontend`, and report remote SHA.
