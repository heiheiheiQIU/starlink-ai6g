# Materials And Frontend Finalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已完成的540次正式运行事实同步到报告、PPT和前端，并明确仍需A/B补齐的发布动作。

**Architecture:** 以B正式分析摘要为唯一数值源，C审计记录为复核依据。报告、PPT和前端共享“技术结果完成、正式发布复核中”的口径；前端继续对未签署结果执行失败关闭，不把技术统计误标为正式结论。

**Tech Stack:** Markdown、python-docx、React/TypeScript/Vitest、@oai/artifact-tool

**Spec:** `docs/superpowers/plans/2026-11-09-formal-results-frontend-plan.md`、`docs/report/report_v3.md`及用户在2026-11-11提出的材料与平台完善要求。

## Global Constraints

- 正式结论只允许“胜、等效、负、未完成”四档，不伪造或美化数据。
- A未完成正式结果复核前，`formal_verdict`保持“未完成”，可展示独立复算后的统计结论“负”。
- 主展示去除H00、WP、A-N4b、门禁、契约、回执等内部研发语言；证据附录可保留文件名与版本标识。
- 报告正文表格继续使用三线表，附录表格使用黑白网格。
- 不生成PDF；DOCX和PPTX必须渲染检查，前端必须通过测试与生产构建。

## Review Focus

- 统计结论为负但发布状态待复核时，三个载体都不得写成“正式负结论已发布”。
- 前端未配置摘要URL时必须显示待接入状态，不能回退到演示数字冒充正式结果。
- 真实摘要为540次完成、零失败、零缺失时必须完整显示。
- 报告与PPT不得继续出现0/540、换机未完成等过期事实。
- AI模型全idle的局限必须解释为数据覆盖和域外泛化问题，不得包装为算法增益。

---

### Task 1: 依赖状态和C发布复核

**Files:**
- Create: `docs/team/C_materials_dependency_status_2026-11-11.md`
- Create: `docs/acceptance/C_formal_results_release_review_2026-11-11.md`

**Interfaces:**
- Consumes: B正式分析摘要与`docs/audits/C_B_formal_results_audit_2026-11-10.md`
- Produces: 材料统一使用的发布边界和待办清单

- [ ] 核对540次运行、两组配对统计、全idle与发布状态。
- [ ] 写清楚无需等待即可完成的材料，以及仍需A/B完成的最小动作。
- [ ] 运行事实检索，确认文档中的数值可追溯。
- [ ] 提交文档。

### Task 2: 报告和PPT统一叙事

**Files:**
- Modify: `docs/report/report_v3.md`
- Modify: `scripts/presentation_story_v2.mjs`
- Test: `tests/presentation_story_v2.test.mjs`
- Generate: `docs/report/星地智调_作品方案_v3.docx`
- Generate: `docs/presentation/generated/星地智调_主讲稿_v3_正式结果工程化版.pptx`

**Interfaces:**
- Consumes: Task 1发布边界与B正式摘要
- Produces: 统一的评委叙事和可交付材料

- [ ] 先更新材料测试，使其拒绝0/540和过期发布措辞并观察失败。
- [ ] 更新报告摘要、实验结果、局限、价值和复现状态。
- [ ] 更新PPT正式实验、正式结果、工程价值与答辩备查页文案。
- [ ] 生成DOCX与PPTX，渲染并检查全部页面和幻灯片。
- [ ] 提交材料源文件与最终文件。

### Task 3: 前端真实摘要和工程措辞

**Files:**
- Modify: `frontend/src/components/FormalResultsPanel.tsx`
- Modify: `frontend/src/components/FormalResultsPanel.test.tsx`
- Modify: `frontend/src/pages/ComparePage.tsx`
- Create: `frontend/public/data/formal_v2_technical_summary.json`

**Interfaces:**
- Consumes: B `formal-analysis-summary-v1`对象
- Produces: 可直接展示真实技术结果、保持发布边界的策略评估页

- [ ] 先修改测试，要求“技术结果完成、发布复核中”的外部措辞并观察失败。
- [ ] 接入真实摘要，保留`result_signoff=pending`和`formal_verdict=未完成`。
- [ ] 清理主页面内部研发措辞，明确真实实验与交互沙盒的差异。
- [ ] 运行前端定向测试、全量测试与生产构建。
- [ ] 提交前端改动。
