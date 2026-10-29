# 成员 C 前端基础与 v4 主舞台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立可离线构建和测试的 React 前端，交付 v4 最终裁定版的应用壳、六步流程主舞台、工作台入口、AI助手占位页、不可移除的契约样例标识及证据索引骨架。

**Architecture:** 新建独立 `frontend/`，使用页面级状态驱动侧栏导航和六步主舞台；本阶段只消费本地契约 fixture，不连接真实 API。可视组件与数据定义分离，后续 H00 合入 `main` 后再用正式 `contracts.ts` 和 B 的 API 适配器替换 fixture 数据源。

**Tech Stack:** React 18.3.1、TypeScript 5.9.3、Vite 6.4.3、ECharts 6.1.0、Vitest 2.1.9、Testing Library、纯 CSS/SVG。

**Spec:** `docs/ui_structure.md`（用户确认的 v4 最终裁定版）；角色与可读性约束同时来自工作区 `审查输出/成员任务书/C_前端与材料执行任务书.md`。

## Global Constraints

- 保留 v4 的六个一级入口、六步流程主舞台、步骤子侧栏、工程师详情区、AI助手页与全局助手入口。
- 当前所有数据显著标注“契约样例 · 非实验结果”，标识不得因页面切换或窄屏隐藏。
- 核心正文与有效辅助文字最小 14px，关键数字最小 24px；状态同时使用文字、图标和颜色。
- 前端不训练模型、不生成实验数字、不重算科学指标、不把历史旧成果冒充当前 run。
- 在线真实值只能进入事后证据区域；当前切片不连接 API，不声称已实现真实闭环。
- 图标、字体、样式与 fixture 全部本地化，不使用 CDN。
- 1920×1080 与 1366×768 均保留流程、fixture 标识、导航和主要操作。

## Review Focus

- 页面切换后 fixture 徽章消失：所有页面必须由同一应用壳包裹并保持徽章可见。
- 六步顺序或当前步骤错乱：上一步/下一步必须有边界，步骤标题和详情同步。
- AI助手占位回答冒充真实 RAG：必须明确为契约样例，并在无证据问题上拒绝编造。
- 1366px 宽度下关键控制被遮挡：布局必须允许侧栏和详情区收纳，主操作仍可见。
- reduced-motion 用户仍被强制动画：CSS 必须关闭非必要动画和过渡。

---

### Task 1: 工程、状态模型与测试基线

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/pnpm-lock.yaml`（安装生成）
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/vite-env.d.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/domain/navigation.ts`
- Create: `frontend/src/domain/navigation.test.ts`

**Interfaces:**
- Produces: `PageId`、`NAV_GROUPS`、`getPageLabel(pageId: PageId): string`，供 Task 2 应用壳使用。
- Consumes: 无。

- [ ] **Step 1: 创建工程配置与失败测试**

测试必须断言六个入口按 v4 顺序分为“主流程/工作台”两组，且 `flow` 标签为“流程主舞台”、`assistant` 标签为“AI 助手”。此时 `src/domain/navigation.ts` 不存在。

- [ ] **Step 2: 安装依赖并运行 RED**

Run: `pnpm install`，随后 `pnpm test -- navigation.test.ts --run`  
Expected: 测试因无法导入 `./navigation` 失败。

- [ ] **Step 3: 实现最小导航状态模型**

`PageId` 固定为 `flow | overview | assistant | compare | evidence | assets`；`NAV_GROUPS` 保存分组和入口，禁止包含旧教育业务。

- [ ] **Step 4: 运行 GREEN 与类型检查**

Run: `pnpm test -- navigation.test.ts --run`  
Expected: PASS。  
Run: `pnpm exec tsc --noEmit`  
Expected: exit 0。

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "chore(frontend): establish tested Vite foundation"
```

### Task 2: v4 应用壳、常驻样例标识与页面导航

**Files:**
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/App.test.tsx`
- Create: `frontend/src/components/AppSidebar.tsx`
- Create: `frontend/src/components/FixtureBanner.tsx`
- Create: `frontend/src/components/PagePlaceholder.tsx`
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/global.css`

**Interfaces:**
- Consumes: `NAV_GROUPS` 与 `PageId` from Task 1。
- Produces: `App` 页面切换壳；Task 3 将 `flow` 占位替换为 `FlowWorkspace`。

- [ ] **Step 1: 写 App 行为失败测试**

使用真实 `App` 断言：初始页面显示“流程主舞台”；常驻横幅包含“契约样例”和“非实验结果”；点击“AI 助手”后显示其页面标题，同时横幅仍存在；导航具备可访问名称和当前项状态。

- [ ] **Step 2: 运行 RED**

Run: `pnpm test -- App.test.tsx --run`  
Expected: 因 `App` 不存在或缺少行为失败。

- [ ] **Step 3: 实现应用壳与视觉令牌**

应用壳使用浅色 Liquid Glass、青蓝/靛蓝主色、深色内容舞台预留；fixture 横幅在主内容顶部常驻。正文 token `--font-body: 14px`，关键数字 token `--font-metric: 24px`。

- [ ] **Step 4: 运行 GREEN、全套测试和类型检查**

Run: `pnpm test -- App.test.tsx --run`  
Expected: PASS。  
Run: `pnpm test -- --run && pnpm exec tsc --noEmit`  
Expected: 全部 PASS / exit 0。

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat(frontend): add v4 application shell"
```

### Task 3: 六步流程主舞台与工程师详情

**Files:**
- Create: `frontend/src/domain/flow.ts`
- Create: `frontend/src/domain/flow.test.ts`
- Create: `frontend/src/pages/FlowWorkspace.tsx`
- Create: `frontend/src/pages/FlowWorkspace.test.tsx`
- Create: `frontend/src/components/FlowStepper.tsx`
- Create: `frontend/src/components/StagePanel.tsx`
- Create: `frontend/src/components/EngineerDetails.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- Produces: `FLOW_STEPS` 六步元数据和 `clampStep(index: number): number`；`FlowWorkspace` 消费它们。
- Consumes: Task 2 的应用壳。

- [ ] **Step 1: 写状态模型失败测试**

断言六步顺序固定；`clampStep(-1)=0`、`clampStep(6)=5`；第5步标题为“发送/确认”，详情产物为 `events.jsonl`。

- [ ] **Step 2: 运行 RED 并实现最小模型**

Run: `pnpm test -- flow.test.ts --run`  
Expected: 因模块不存在失败；实现后再次运行并 PASS。

- [ ] **Step 3: 写主舞台行为失败测试**

断言初始为第1步；点击“下一步”进入“窗口预测”；点击步骤5进入“发送/确认”；工程师详情默认收起，展开后显示当前步骤产物和“契约样例”。

- [ ] **Step 4: 运行 RED 并实现主舞台**

Run: `pnpm test -- FlowWorkspace.test.tsx --run`  
Expected: 因组件不存在或行为缺失失败；实现最小组件后 PASS。

- [ ] **Step 5: 全量验证与构建**

Run: `pnpm test -- --run`  
Expected: 全部 PASS。  
Run: `pnpm build`  
Expected: TypeScript 与 Vite 构建 exit 0，生成 `frontend/dist/`。

- [ ] **Step 6: Commit**

```bash
git add frontend
git commit -m "feat(frontend): build six-step operations stage"
```

### Task 4: AI助手契约样例与证据索引骨架

**Files:**
- Create: `frontend/src/domain/assistant.ts`
- Create: `frontend/src/domain/assistant.test.ts`
- Create: `frontend/src/pages/AssistantPage.tsx`
- Create: `frontend/src/pages/AssistantPage.test.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `docs/evidence_index.md`

**Interfaces:**
- Produces: `answerFixtureQuestion(question: string): FixtureAnswer`，只返回预置引用或拒绝编造；证据索引供后续真实 run 填充。
- Consumes: Task 2 的 `assistant` 页面入口。

- [ ] **Step 1: 写助手边界失败测试**

断言询问“数字是真的吗”返回 fixture 声明和证据路径；未知问题返回拒绝编造，且不得包含百分比收益；返回值带 `isFixture=true`。

- [ ] **Step 2: 运行 RED 并实现最小回答器**

Run: `pnpm test -- assistant.test.ts --run`  
Expected: 因模块不存在失败；实现后 PASS。

- [ ] **Step 3: 写并实现页面行为**

测试真实 `AssistantPage`：输入未知问题并提交后显示拒绝编造；页面常驻“契约样例”；引用区域显示本地文档路径。先 RED，再实现至 GREEN。

- [ ] **Step 4: 创建证据索引骨架**

表头固定为 `claim_id | 结论 | 证据等级 | run_id | policy_id | 源文件 | 生成命令 | 图表路径 | 负责人签核 | 可支持 | 不可支持`；所有未有真实结果的条目标为“待真实 run”，不得写 0。

- [ ] **Step 5: 全量验证、构建和可访问性静态检查**

Run: `pnpm test -- --run`  
Expected: 全部 PASS。  
Run: `pnpm build`  
Expected: exit 0。  
Run: `rg -n "font-size:\s*(9|10|11|12|13)(px|rem)" src`  
Expected: 不得发现以 px 表示的小于14px有效文本；命中必须人工说明仅为非文本装饰，否则修复。

- [ ] **Step 6: Commit**

```bash
git add frontend docs/evidence_index.md
git commit -m "feat(frontend): add fixture-safe assistant and evidence index"
```
