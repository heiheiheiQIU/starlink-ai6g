# Mission Visual Language Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将七页前端统一升级为克制、可发布的星地任务控制台，并完成面向评委与工程师的双层产品措辞。

**Architecture:** 用集中式产品词汇表约束用户可见措辞，以语义色彩令牌统一全站状态表达；生成单一主题背景资产，通过全局工作区伪元素低透明叠加，不进入数据卡内部。现有页面结构、接口和业务状态机保持不变。

**Tech Stack:** React 19、TypeScript、CSS、Vitest、Testing Library、Vite、PNG/WebP 背景资产

**Spec:** `docs/superpowers/specs/2026-11-06-mission-visual-language-design.md`

## Global Constraints

- 不改变后端接口、合同字段、科学指标和正式实验四档口径。
- 第一层不出现未解释的 `FIXTURE`、`MIXED`、`DEV-RUN`。
- 用户第一层使用“任务实例”，工程详情保留 `run_id`。
- 背景无文字、无人像、无 UI 框，不承载数据事实。
- 动效遵守 `prefers-reduced-motion`，非活动组件不持续泛光。

## Review Focus

- 演示数据与在线任务视觉相近时仍必须能通过文字辨认来源。
- 1366×768 下主题背景和半透明面板不得降低正文对比度。
- 长中文来源说明在窄屏不得挤压主操作。
- 专业词替换不得改动 JSON 字段、类型名、API 路径和测试夹具。
- 背景资产加载失败时仍保持完整的纯色渐变基底。

---

### Task 1: 产品词汇表与数据来源语言

**Files:**
- Create: `frontend/src/domain/productLanguage.ts`
- Create: `frontend/src/domain/productLanguage.test.ts`
- Modify: `frontend/src/domain/dataSource.ts`
- Modify: `frontend/src/domain/navigation.ts`
- Modify: `frontend/src/App.test.tsx`

**Interfaces:**
- Produces: `PRODUCT_TERMS`、`sourceLabel(kind: DataSourceKind): string`

- [ ] 写失败测试，断言七页来源 badge 为中文业务名称，且核心词映射包含“任务实例 / 安全约束决策 / 最优决策标注”。
- [ ] 运行定向测试，确认因词汇表不存在和旧英文 badge 而失败。
- [ ] 实现词汇表并替换页面来源说明与导航名称。
- [ ] 运行定向测试，确认通过。

### Task 2: 七页用户可见措辞迁移

**Files:**
- Modify: `frontend/src/pages/*.tsx`
- Modify: `frontend/src/components/*.tsx`
- Modify: `frontend/src/domain/flow.ts`
- Modify: corresponding `*.test.tsx`

**Interfaces:**
- Consumes: `PRODUCT_TERMS`

- [ ] 在现有页面测试中增加第一层标题与状态文案断言，并禁止孤立英文来源 badge。
- [ ] 运行测试确认旧措辞导致失败。
- [ ] 逐页迁移第一层文案，工程详情保留接口字段和英文标识。
- [ ] 运行页面测试确认通过。

### Task 3: 主题背景资产与视觉令牌

**Files:**
- Create: `frontend/public/visuals/orbital-command-backdrop-v1.png`
- Modify: `frontend/src/styles/tokens.css`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- Produces: 语义色彩变量与 `.app-main::before` 背景层

- [ ] 生成无文字、低对比、16:9 星地主题背景并复制到项目资产目录。
- [ ] 用 CSS 静态检查测试或现有 App 测试断言根节点主题类与背景资产路径。
- [ ] 运行测试确认旧样式失败。
- [ ] 重构令牌和全局面板样式，保留纯色渐变回退。
- [ ] 运行定向测试确认通过。

### Task 4: 动效克制与响应式验收

**Files:**
- Modify: `frontend/src/styles/global.css`
- Modify: `frontend/src/pages/FlowWorkspace.test.tsx`

**Interfaces:**
- Consumes: Task 3 语义色彩令牌

- [ ] 增加运行态/非运行态语义测试，确保只有 playing 状态出现运行扫描标识。
- [ ] 删除常驻金色按钮脉冲，把循环动效限制在运行、通信和告警状态。
- [ ] 运行完整前端测试、`tsc --noEmit` 与生产构建。
- [ ] 用浏览器检查 1366×768、1440×1000 七页和真实离线状态，记录控制台错误。

### Task 5: 审计、视觉证据与版本归档

**Files:**
- Create: `docs/acceptance/C_visual_language_acceptance_2026-11-06.md`
- Modify: `docs/WORKSPACE_CONTEXT.md`（若存在）

**Interfaces:**
- Produces: 本轮色彩、措辞、测试与人工验收回执

- [ ] 搜索用户可见源码，确认未解释的内部措辞已清理或仅存在工程详情。
- [ ] 记录背景资产来源、色彩语义、测试数量、构建结果和已知边界。
- [ ] 执行 `git diff --check` 和最终全量验证。
- [ ] 提交本轮修改；远端推送前报告提交号。

