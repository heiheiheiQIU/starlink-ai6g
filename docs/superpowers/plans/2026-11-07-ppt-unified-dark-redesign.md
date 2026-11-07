# 星地智调 PPT 统一特色背景重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 15 页 v0 主讲稿重构为以项目星地特色图贯穿全稿、浅色证据卡片承载图表、图旁配置业务解释的 v1 统一视觉版本。

**Architecture:** 保留现有内容顺序和四档结果口径，在 `scripts/build_presentation.mjs` 中建立统一背景、标题、证据卡片、解释区和结论带的可复用布局函数。现有科研图作为证据资产嵌入卡片，不再整页铺满；最终通过 Artifact Tool 生成、渲染和验证 PPTX。

**Tech Stack:** JavaScript、`@oai/artifact-tool`、现有 PNG/SVG 图件、演示文稿验证工具

**Spec:** `docs/superpowers/specs/2026-11-07-ppt-unified-dark-redesign.md`

## Global Constraints

- 15 页全部使用项目自有星地特色图，不出现整页纯白背景。
- 正文页使用深蓝半透明蒙层，但卫星、地球弧面和通信光链仍可辨识。
- 浅色卡片只承载证据，页面旁侧必须解释证据的业务意义。
- 第 11 页保持“未完成”，不得加入未经 A/B/C 签核的正式结果数字。
- 不改变现有数据、实验关系和证据结论。
- 字体使用微软雅黑，正文不低于 17 pt，图注不低于 11 pt。

## Review Focus

- 背景过暗：正文页仍应能识别卫星、地球弧面和通信链路。
- 图件重复标题：PPT 主标题与图内标题不能形成两个竞争焦点。
- 浅色卡片过大：不得再次产生“整页白底”的观感。
- 解释区退化为图中文字复述：解释必须回答业务意义或证据边界。
- 结果页误导：待签核状态必须在缩略图和全屏状态下都清楚可见。

---

### Task 1: 统一视觉系统与背景层

**Files:**
- Modify: `scripts/build_presentation.mjs`

**Interfaces:**
- Consumes: `docs/figures/generated/v2/C-F00_星地智调主题背景_v1.png`
- Produces: `addThemeBackground(slide, options)`、`addPageHeader(slide, section, title, subtitle)`、`addEvidenceCard(slide, options)`、`addInsightPanel(slide, options)`

- [x] **Step 1: 建立背景与母版辅助函数**

实现固定特色图背景、深蓝蒙层、章节编号、标题线和页码，参数允许正文页与封面页使用不同可见度。

- [x] **Step 2: 添加布局守卫**

对卡片宽高、边距和字体设置固定常量，确保白色内容面积不超过正文页约 72%，解释区不少于页面宽度约 22%。

- [x] **Step 3: 生成三页代表性预览**

生成封面、单证据页和双证据页，确认背景特征可辨识且文字对比度足够。

### Task 2: 重构证据与流程页面

**Files:**
- Modify: `scripts/build_presentation.mjs`

**Interfaces:**
- Consumes: Task 1 的四个布局函数及 `docs/figures/generated/v2/previews/*.png`
- Produces: 第 3–7 页、第 9–14 页统一卡片布局

- [x] **Step 1: 将现有整页科研图改为卡片内图件**

按内容选择单证据、双证据或中央流程卡片，禁止任何白底图覆盖整页。

- [x] **Step 2: 为每页增加独立解释区**

解释区写清本页证据、评委应读取的结论和边界，不复述图中标签。

- [x] **Step 3: 保持第 11 页安全占位**

使用橙色“待三方签核”状态和未完成说明，不出现效果数字。

### Task 3: 重构封面、问题页、安全页与结束页

**Files:**
- Modify: `scripts/build_presentation.mjs`

**Interfaces:**
- Consumes: Task 1 的背景与标题系统
- Produces: 第 1、2、8、15 页定制布局

- [x] **Step 1: 调整封面与结束页**

提高特色背景可见度，压缩文字组数，保持卫星和通信光链为视觉主体。

- [x] **Step 2: 重做业务迫切性页**

使用一块主叙事区和三条事实，不做白色卡片阵列。

- [x] **Step 3: 重做安全约束页**

用一张浅色约束证据卡片配一块深色回退解释区，减少网页仪表盘感。

### Task 4: 生成、验证与里程碑提交

**Files:**
- Modify: `docs/presentation/星地智调_PPT制作方案_2026-11-07.md`
- Create: `docs/presentation/generated/星地智调_主讲稿_v1_统一特色背景版.pptx`
- Modify: `scripts/build_presentation.mjs`

**Interfaces:**
- Consumes: Task 1–3 的完整 15 页生成逻辑
- Produces: 可交付 PPTX、渲染预览和验证回执

- [x] **Step 1: 生成全部 15 页与缩略图**

运行生成脚本并导出逐页 PNG 和 montage。

- [x] **Step 2: 逐页视觉检查**

检查背景连续性、标题层级、卡片比例、文字可读性和图旁解释；发现问题后回到所属任务修正。

- [x] **Step 3: 执行自动验证**

验证包结构、15 页数量、16:9 尺寸、布局、微软雅黑字体和首次导入，期望 0 项布局错误与 0 项警告。

- [x] **Step 4: 更新状态并提交**

仅提交设计说明、实施计划、生成脚本、v1 PPTX和方案状态，不提交临时渲染文件或 Word 锁文件。
