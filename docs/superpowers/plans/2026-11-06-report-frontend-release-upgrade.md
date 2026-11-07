# Report and Frontend Release Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有作品方案与七页前端从“可读初稿/可演示页面”提升为证据口径严谨、版式可提交、状态可追踪的正式发布候选。

**Architecture:** 文档以 Markdown 为单一内容源，由构建脚本生成带 A4 页面、正式样式、表格规则、公式编号与交叉引用的 DOCX；前端在现有页面结构之上增加统一运行会话状态，让演示模式与真实运行模式共用状态机和视觉语义。两条线分别验收，最终以材料门禁、DOCX 渲染检查和前端测试/构建/桌面视口检查汇合。

**Tech Stack:** Markdown、Pandoc、python-docx、OOXML、React 18、TypeScript、Vitest、Vite、CSS/SVG。

**Spec:** `docs/audits/C_DS_material_frontend_audit_2026-11-06.md`

## Global Constraints

- 保留现有最终裁定版页面信息架构与用户确定的界面方向，仅做增量升级。
- 所有材料数字必须来自 `claims_spec.json`；pending 主张只能以占位/验证计划呈现。
- 四档口径固定为胜/等效/负/未完成；“等效档”必须解释为“未检出稳定差异”，不得伪装为严格等效检验。
- FIXTURE、REAL RUN、SIGNED-OFF 三种数据状态必须显式区分。
- 不出现学校、团队成员、指导教师等身份信息。
- 所有新增前端行为先写失败测试；全部修改须通过全量测试与构建。

## Review Focus

- 后端离线或运行失败时，界面应保留最后可核验状态并显示恢复动作，而非假装在线。
- fixture 与 real run 切换时，任何旧指标都不得继续以真实数据样式展示。
- 自动、暂停、单步三种控制必须推进同一个运行状态机，不能各自维护互相矛盾的状态。
- 1366×768 投屏下不得出现主内容横向滚动或关键控制被遮挡。
- DOCX 中长表跨页必须重复表头，公式引用必须随编号变化保持一致。

---

### Task 1: 修正文档事实口径与内容结构

**Files:**
- Modify: `docs/report/report_v2.md`
- Modify: `docs/materials/claims_spec.json`

**Interfaces:**
- Consumes: `claims_spec.json` 的 signed_off/pending 状态。
- Produces: 无占位参考文献、无错配数字、可由构建器转换的正式 Markdown。

- [ ] 修正 claim-E1、四档统计表述、笔误和错误标签。
- [ ] 将正文 18 工况全表降为结论型摘要，并把完整矩阵保留到附录。
- [ ] 补齐可核验的教师求解、调度/链路、数据集与软件引用；删除无法核验的占位项。
- [ ] 按“真实需求→AI+6G机制→工程闭环→证据边界→推广路径”加强每章开头和结尾。
- [ ] 运行材料门禁，确认 pending 主张未进入正式结果口径。

### Task 2: 重构 DOCX 正式版式生成器

**Files:**
- Modify: `scripts/build_report_docx.py`
- Create: `scripts/tests/test_build_report_docx.py`
- Regenerate: `docs/report/reference_official.docx`
- Regenerate: `docs/report/星地智调_作品方案_v2.docx`

**Interfaces:**
- Consumes: `report_v2.md`。
- Produces: A4、单倍行距、正式表格样式、可稳定编号/引用的 DOCX。

- [ ] 先写失败测试：A4 页尺寸、页边距、字体、表头重复、单元格边距、公式 `SEQ` 域和交叉引用不存在时失败。
- [ ] 明确设置 A4 `21.0×29.7 cm`，修复现有 reference 文档不再因文件已存在而跳过校正。
- [ ] 建立标题/正文/图题/表题/公式/参考文献样式；中文宋体、英文和数字 Times New Roman。
- [ ] 表格按列数和语义分配宽度，设置浅色表头、细灰边框、重复表头、行不拆页和小五号字。
- [ ] 使用 Word 字段实现公式 `SEQ Equation` 与书签/`REF`，消除 `式(eq:...)` 等源标签。
- [ ] 构建 DOCX，导出 PDF/页面 PNG，并逐页检查溢出、孤行、表格和公式。

### Task 3: 建立统一运行会话与工程状态带

**Files:**
- Create: `frontend/src/domain/runSession.ts`
- Create: `frontend/src/domain/runSession.test.ts`
- Create: `frontend/src/components/OperationsBar.tsx`
- Create: `frontend/src/components/OperationsBar.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/FlowWorkspace.tsx`

**Interfaces:**
- Produces: `RunSessionState`、`RunMode`、`RunPhase`、`advanceRunSession()`。
- Consumes: 现有 `FLOW_STEPS` 与页面数据源状态。

- [ ] 先写失败测试：模式切换清空旧真实指标、单步只推进一步、失败保持可恢复状态、证据冻结状态不可伪造。
- [ ] 实现纯函数状态机和运行会话状态。
- [ ] 新增工程状态带：数据源、API 状态、run_id、最近同步、证据状态、恢复/切换动作。
- [ ] 让自动/暂停/单步控制共用状态机；真实模式无后端时明确降级为只读/离线。
- [ ] 运行定向测试和全量测试。

### Task 4: 统一视觉系统与状态驱动动效

**Files:**
- Modify: `frontend/src/styles/tokens.css`
- Modify: `frontend/src/styles/global.css`
- Modify: `frontend/src/components/StageExperience.tsx`
- Modify: `frontend/src/components/DemoOverlay.tsx`
- Modify: `frontend/src/pages/FlowWorkspace.test.tsx`

**Interfaces:**
- Consumes: `RunPhase` 与状态机动作。
- Produces: 统一语义色、运行脉冲轨、状态驱动链路动效、1366×768 紧凑布局。

- [ ] 先写失败测试：工程状态带存在、当前阶段有唯一 active 标记、单步推进文案与状态一致、链路失败显示失败而非继续 ACK。
- [ ] 收敛色板并为 AI/链路/成功/风险/阻断建立唯一 token。
- [ ] 在六步导航和主舞台之间增加贯穿式运行脉冲轨，仅当前阶段发光。
- [ ] 将链路包、ACK、拒绝、证据生成动效绑定状态，不再依赖彼此独立的本地布尔值。
- [ ] 增加 1366×768 紧凑布局与 reduced-motion 降级。
- [ ] 检查七页的卡片、图表、状态徽章与数据源提示一致性。

### Task 5: 发布前联合验证

**Files:**
- Modify: `docs/acceptance/C_release_candidate_2026-11-06.md`

**Interfaces:**
- Consumes: Tasks 1–4 的产物。
- Produces: 可供 A/B/C 三方复核的发布候选回执。

- [ ] 运行前端全量测试、类型检查与生产构建，记录测试数与产物大小。
- [ ] 运行材料门禁和 DOCX 结构测试。
- [ ] 渲染并逐页检查 DOCX；在 1440×900 和 1366×768 检查七页前端及关键动效。
- [ ] 检查浏览器控制台无错误，键盘焦点、禁用态和 reduced-motion 可用。
- [ ] 写回执，逐条列明已完成、未完成、证据路径和禁止写入正式材料的 pending 项。
