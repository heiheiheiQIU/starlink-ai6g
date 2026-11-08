# Scientific Report Figure Samples Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成C-F03、A-F02、B-F02三张白底科研报告样板图，建立可复用的报告图生成与验收基线。

**Architecture:** 新建独立报告图生成器，不覆盖v2的PPT图件。生成器输出物理尺寸明确的SVG；Python结构测试检查背景、装饰禁令、字体、关键事实和文件边界，人工审阅负责排版与视觉质量。

**Tech Stack:** Node.js原生SVG生成、Python unittest/pytest、SVG/XML、Git。

**Spec:** `docs/superpowers/specs/2026-11-08-scientific-report-figure-design.md`

## Global Constraints

- v2图件继续供PPT使用，不得覆盖。
- 报告图纯白底，无阴影、渐变、徽章和内部大标题。
- 数字与结论不得突破现有签核事实；正式运行未完成的口径不变。
- 输出SVG母版与PNG预览；本阶段不生成或改写报告PDF。
- 不触碰未跟踪的Word锁文件。

## Review Focus

- SVG缩放至165 mm后字号是否仍可读：Task 2人工渲染审阅。
- 中文字体不可用时是否出现截断：Task 2人工渲染审阅与文本边界检查。
- 图内是否重复Word图题：Task 1禁用内部标题断言。
- 机制箭头是否穿字或方向含混：Task 2逐图审阅。
- 数据口径是否被视觉元素夸大：Task 1关键事实断言与Task 2内容复核。

---

### Task 1: 科研图形合同测试

**Files:**
- Create: `scripts/tests/test_scientific_report_figures.py`

**Interfaces:**
- Consumes: 设计规范中的文件名、视觉禁令和三图事实。
- Produces: `node scripts/generate_report_figures_v3.mjs`的可执行合同。

- [ ] **Step 1: 编写失败测试**，要求三张SVG存在、物理宽度为170 mm、根背景纯白、无`filter`/渐变/内部徽章/内部大标题，并包含各自关键事实。
- [ ] **Step 2: 运行测试并确认因生成器或输出缺失而失败。**
- [ ] **Step 3: 提交测试合同。**

### Task 2: 三张样板SVG生成器

**Files:**
- Create: `scripts/generate_report_figures_v3.mjs`
- Create: `docs/figures/generated/v3/report/C-F03_AI与6G双向耦合_报告版.svg`
- Create: `docs/figures/generated/v3/report/A-F02_教师标签质量审计_报告版.svg`
- Create: `docs/figures/generated/v3/report/B-F02_能量账本校核_报告版.svg`
- Create: `docs/figures/generated/v3/report/manifest.json`
- Create: `docs/figures/generated/v3/report/README.md`

**Interfaces:**
- Consumes: Task 1合同。
- Produces: 可供后续报告接入与全套图迁移复用的SVG样板和统一绘图原语。

- [ ] **Step 1: 实现共享色板、字体、文字、线条、箭头、坐标和面板标记原语。**
- [ ] **Step 2: 实现C-F03机制图。**
- [ ] **Step 3: 实现A-F02三面板审计图。**
- [ ] **Step 4: 实现B-F02三面板工程校核图。**
- [ ] **Step 5: 生成manifest并运行Task 1测试至通过。**
- [ ] **Step 6: 渲染并逐图检查留白、对齐、箭头、字号、数字与边界说明。**
- [ ] **Step 7: 提交样板图。**

### Task 3: 样板审计与迁移说明

**Files:**
- Create: `docs/audits/C_scientific_report_figure_samples_review_2026-11-08.md`

**Interfaces:**
- Consumes: Task 2三张SVG与manifest。
- Produces: 视觉审计结论、已知限制和其余九张图的迁移顺序。

- [ ] **Step 1: 按设计规范逐条审计三张样板。**
- [ ] **Step 2: 运行图形合同测试与现有报告构建器测试。**
- [ ] **Step 3: 记录迁移顺序和需要用户确认的视觉选择。**
- [ ] **Step 4: 提交审计记录。**
