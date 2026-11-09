# Sandbox Demo Routes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有真实沙盒中加入三条黄金演示路线、配置差异、运行进度/失败操作和中性结果解读。

**Architecture:** 路线与结果解读放在纯领域模块，React组件只管理编辑快照和运行交互；所有请求继续通过同一 `RunController`。不保存固定结果。

**Tech Stack:** React 18、TypeScript、Vitest、Testing Library。

**Spec:** `docs/superpowers/specs/2026-11-09-sandbox-demo-routes-design.md`

## Global Constraints

- 浏览器只提交 `sandbox-axis-v1` 轴合同。
- 合成结果不替代正式实验，负结果不美化。
- 不触碰用户报告PDF删除和Word锁文件。

## Review Focus

- 路线参数必须与B的S1/S2/S3完全一致。
- 切换路线不能自动提交。
- 修改参数后旧结果必须标记历史结果。
- 进度为null时不得伪造百分比。
- 结果解释必须覆盖胜、等效、负、缺失四类事实状态。

---

### Task 1: 路线与解释领域模型

**Files:** Modify `frontend/src/domain/sandbox.ts`; Test `frontend/src/domain/sandbox.test.ts`。

- [x] 先写失败测试，固定S1/S2/S3轴值、配置差异和四类结果解释。
- [x] 运行定向测试确认RED。
- [x] 实现 `SANDBOX_DEMO_ROUTES`、`diffSandboxAxes`、`explainSandboxResults`。
- [x] 运行定向测试确认GREEN。

### Task 2: 工程交互面板

**Files:** Modify `frontend/src/components/SandboxControlPanel.tsx`、测试与 `frontend/src/styles/global.css`。

- [x] 先写失败测试，覆盖路线填充不自动POST、进度、后台监控、失败与配置差异。
- [x] 运行定向测试确认RED。
- [x] 实现路线卡、运行快照、差异区、进度和错误操作。
- [x] 运行定向测试确认GREEN。

### Task 3: 全量验证

- [x] 运行前端全量测试、TypeScript检查和生产构建。
- [x] 浏览器实际执行S1/S2/S3并检查页面结果变化与控制台错误。
- [x] 检查差异和用户文件边界，提交本地里程碑。
