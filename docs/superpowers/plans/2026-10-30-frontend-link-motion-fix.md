# Frontend Link Motion Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让发送/确认页面的 GW、SAT、上行数据块和下行 ACK 严格共用一条链路，并清理最终展示界面中的内部研发管理话语。

**Architecture:** 使用一个 SVG 坐标系同时绘制 GW、SAT、链路线和两个方向的运动图元，消除多套 CSS 坐标漂移。产品文案保留“演示数据、非实验结果”的证据边界，但移除成员代号、分支、内部截止和研发缺陷编号。

**Tech Stack:** React 18、TypeScript、SVG、CSS、Vitest、Testing Library

**Spec:** `docs/ui_structure.md`；补充问题清单：工作区 `前端图片/查出问题.md`

## Global Constraints

- 保留已批准的六步流程、深色主舞台和现有交互。
- 数据发送为 GW→SAT；ACK 为 SAT→GW，必须沿同一几何路径反向运动。
- 支持响应式宽度和 `prefers-reduced-motion`。
- 用户界面不得出现成员任务代号、Git 分支、内部截止或缺陷编号。
- 演示数据必须继续明确标注为“演示数据/非实验结果”。

## Review Focus

- 容器宽度变化时节点、光束和运动图元仍共线。
- ACK 丢失时只隐藏 ACK，不改变 GW→SAT 数据路径。
- 暂停状态不应显示运动中的数据块或 ACK。
- 减少动态效果设置下仍可读出发送方向和状态。
- 所有主要页面都不泄露内部任务代号和研发状态。

---

### Task 1: 共线路径回归测试与 SVG 链路

**Files:**
- Modify: `frontend/src/components/StageExperience.tsx`
- Modify: `frontend/src/pages/FlowWorkspace.test.tsx`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- Consumes: `playing: boolean`、`ackLost: boolean`
- Produces: 可访问名称为“GW 到 SAT 数据链路”的 SVG；上行与 ACK 运动路径属性

- [x] **Step 1: 写失败测试**

断言光束路径与数据块 `animateMotion.path` 完全一致，ACK 路径是同一端点的反向路径，并验证 ACK 丢失后不再渲染 ACK 图元。

- [x] **Step 2: 运行定向测试并确认因现有多套 CSS 坐标而失败**

Run: `node_modules/.bin/vitest.cmd run src/pages/FlowWorkspace.test.tsx`

- [x] **Step 3: 将轨道场景改为单一 SVG 坐标系**

节点、光束和运动图元全部使用固定 `viewBox`；数据块正向、ACK 反向；删除重复 `packetFly`/`ackFly` 坐标动画。

- [x] **Step 4: 运行定向测试并确认通过**

Run: `node_modules/.bin/vitest.cmd run src/pages/FlowWorkspace.test.tsx`

### Task 2: 产品化文案边界

**Files:**
- Modify: `frontend/src/pages/OverviewPage.tsx`
- Modify: `frontend/src/pages/OverviewPage.test.tsx`
- Modify: `frontend/src/components/AppSidebar.tsx`
- Modify: `frontend/src/components/FixtureBanner.tsx`
- Modify: `frontend/src/pages/AssetsPage.tsx`
- Modify: `frontend/src/pages/ComparePage.tsx`
- Modify: `frontend/src/pages/EvidencePage.tsx`

**Interfaces:**
- Produces: 只呈现系统运行态势、模型能力和演示数据边界的用户界面文案

- [x] **Step 1: 写失败测试**

在总览和资产页面断言不出现 `A-N*`、`B-R*`、`main`、内部提交倒计时、缺陷编号等研发管理词。

- [x] **Step 2: 运行测试并确认当前文案导致失败**

- [x] **Step 3: 用产品状态替换内部研发状态**

保留演示数据真实性提示；总览改为链路、可用服务与运行态势；资产页改为模型能力、版本和接入状态。

- [x] **Step 4: 运行相关页面测试并确认通过**

### Task 3: 完整验证与视觉复验

**Files:**
- Verify: `frontend/`

- [x] **Step 1: 运行全部前端测试**

Run: `node_modules/.bin/vitest.cmd run`

- [x] **Step 2: 运行 TypeScript 与生产构建**

Run: `node_modules/.bin/tsc.cmd --noEmit`，然后 `node_modules/.bin/vite.cmd build`

- [x] **Step 3: 在浏览器中播放发送、ACK 和 ACK 丢失三种状态**

确认 GW/SAT/光束/1024B/ACK 同线，且页面无内部研发管理信息。
