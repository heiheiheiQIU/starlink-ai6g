# 星地智调 PPT 高信息密度重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成一套保留星地特色背景、包含 15 页主讲与 5 页追问备份、每页形成“判断—证据—解释—业务含义”闭环的高信息密度 PPTX。

**Architecture:** 保留 v1 与现有图件不动，新建 v2 的内容合同、布局组件和生成入口。内容合同集中控制标题、证据、口径和来源，布局组件提供六类可复用但不单调的页面结构，生成入口负责资源装配、导出、验证和逐页预览。

**Tech Stack:** Node.js 22 bundled runtime、`@oai/artifact-tool`、项目现有 SVG/PNG 证据图、Node test runner、PowerPoint 页面级目检。

**Spec:** `docs/superpowers/specs/2026-11-08-ppt-evidence-dense-redesign.md`

## Global Constraints

- 主讲版固定 15 页，备份页固定 5 页；备份页不进入默认播放路径。
- 全稿继续使用 `frontend/public/visuals/orbital-command-backdrop-v1.png` 作为项目主题母题。
- 正式效果仅允许“胜、等效、负、未完成”四档；未签核前第 11 页保持“未完成”。
- Guard 只能表述为观测条件下的可行性检查，不得表述为物理安全保证。
- 合成环境和演示数据不得表述为真实在轨部署；不得披露身份信息。
- 六张 v4 证据总图只能按页面问题裁切或拆解，不得整张缩小后充当全部内容。
- 正文文字以 18—24 pt 为主，脚注不低于 10.5 pt；静态导出必须完整可读。
- 最终文件写入 `docs/presentation/generated/星地智调_主讲稿_v2_高信息密度版.pptx`，不得覆盖 v1。

## Review Focus

- 正式结果仍未签核时：第 11 页不得出现收益数字或暗示“胜”的配色和措辞；Task 1 的口径测试负责锁定。
- 图件或截图缺失时：生成器必须给出包含文件路径的错误，而不是导出空白卡片；Task 3 的资源测试负责锁定。
- 内容长度超过版式容量时：验证必须报告具体页码和文本框，不得通过低于最小字号静默缩放；Task 2 的几何测试负责锁定。
- Guard 页面出现“绝对安全、不能突破”等词时：内容合同测试必须失败；Task 1 负责锁定。
- 备份页误入 15 页默认主讲路径时：章节与页数测试必须失败；Task 4 负责锁定。

---

### Task 1: 建立 20 页叙事与证据合同

**Files:**
- Create: `scripts/presentation_story_v2.mjs`
- Create: `tests/presentation_story_v2.test.mjs`

**Interfaces:**
- Consumes: `docs/superpowers/specs/2026-11-08-ppt-evidence-dense-redesign.md`、已签核证据路径和 v4 图件清单。
- Produces: `MAIN_SLIDES: SlideSpec[15]`、`BACKUP_SLIDES: SlideSpec[5]`、`SLIDE_GUARDRAILS`。`SlideSpec` 至少包含 `id`、`section`、`title`、`claim`、`layout`、`evidence`、`supportingFacts`、`businessMeaning`、`sourceNote`、`status`。

- [ ] **Step 1: 编写失败测试，锁定页数、顺序和必填信息**

测试断言 `MAIN_SLIDES.length === 15`、`BACKUP_SLIDES.length === 5`，正文第 2—14 页均含主证据、至少两项辅助信息、业务结论和来源/口径字段。

- [ ] **Step 2: 编写失败测试，锁定诚实口径**

测试扫描全部可见文案，拒绝“绝对安全、不能被突破、全面优于、在轨部署”；第 11 页必须包含“未完成”和四档口径，且不得包含百分比提升。

- [ ] **Step 3: 运行测试并确认失败**

Run: `node --test tests/presentation_story_v2.test.mjs`  
Expected: FAIL，提示 `presentation_story_v2.mjs` 或导出项不存在。

- [ ] **Step 4: 实现 `presentation_story_v2.mjs`**

按设计文档第 5、6 节写入 15 页主讲和 5 页备份的完整内容合同；外部事实写明文献，内部数字写明证据路径或“设计参数”。

- [ ] **Step 5: 运行测试并确认通过**

Run: `node --test tests/presentation_story_v2.test.mjs`  
Expected: PASS。

- [ ] **Step 6: 提交叙事合同**

```bash
git add scripts/presentation_story_v2.mjs tests/presentation_story_v2.test.mjs
git commit -m "feat(presentation): define evidence-dense story contract"
```

### Task 2: 建立六类高信息密度布局组件

**Files:**
- Create: `scripts/presentation_layouts_v2.mjs`
- Create: `tests/presentation_layouts_v2.test.mjs`
- Reference: `scripts/presentation_design.mjs`
- Reference: `scripts/build_presentation.mjs`

**Interfaces:**
- Consumes: `SlideSpec`、`Presentation`、主题资产和颜色合同。
- Produces: `addThemeBackground()`、`addClaimHeader()`、`addEvidencePanel()`、`addMetricStrip()`、`addInterpretation()`、`addSourceNote()`，以及 `renderScenarioTimeline()`、`renderComparisonMatrix()`、`renderMechanismChain()`、`renderExperimentProtocol()`、`renderEngineeringBoundary()`、`renderProductEvidence()`。

- [ ] **Step 1: 编写失败测试，锁定六类布局和最小字号**

测试断言六类渲染器均导出；主文本字号不低于 18 pt、来源不低于 10.5 pt；布局不得回退为连续十页相同的“大白框＋右侧说明”。

- [ ] **Step 2: 编写失败测试，锁定页面几何和缺失资源行为**

测试断言所有组件坐标位于 1600×900 画布内；`addEvidencePanel()` 接收不存在的资源时抛出包含绝对资源路径的错误。

- [ ] **Step 3: 运行测试并确认失败**

Run: `node --test tests/presentation_layouts_v2.test.mjs`  
Expected: FAIL，提示布局模块不存在。

- [ ] **Step 4: 实现主题、信息层级和六类布局组件**

沿用深蓝星地背景，将浅色容器拆成局部证据区；组件必须支持主图、局部放大、指标条和结论条组合，不在组件内部写业务文案。

- [ ] **Step 5: 运行测试并确认通过**

Run: `node --test tests/presentation_layouts_v2.test.mjs`  
Expected: PASS。

- [ ] **Step 6: 提交布局组件**

```bash
git add scripts/presentation_layouts_v2.mjs tests/presentation_layouts_v2.test.mjs
git commit -m "feat(presentation): add evidence-dense slide layouts"
```

### Task 3: 生成并验证 15 页主讲版

**Files:**
- Create: `scripts/build_presentation_v2.mjs`
- Create: `tests/presentation_build_v2.test.mjs`
- Read: `docs/figures/generated/v4/report/`
- Read: `frontend/public/visuals/`
- Output: `.presentation-build/v2/slide-01.png` through `slide-15.png`

**Interfaces:**
- Consumes: `MAIN_SLIDES` 和 Task 2 的布局接口。
- Produces: `buildMainDeck(presentation): Promise<void>`、15 张主讲页预览、主讲页清单与资源 manifest。

- [ ] **Step 1: 编写失败测试，锁定 15 页内容与资源**

测试断言每个 `SlideSpec` 的布局已注册、引用资源存在、首页与末页使用 hero 版式、第 8 页含预测约束与真值违例边界、第 11 页状态为 `pending`。

- [ ] **Step 2: 运行测试并确认失败**

Run: `node --test tests/presentation_build_v2.test.mjs`  
Expected: FAIL，提示生成入口不存在。

- [ ] **Step 3: 实现 `buildMainDeck()` 和主讲资源装配**

逐页使用 Task 1 指定的布局与证据；六张 v4 总图按问题选用局部面板或重组为可编辑标注，不更改其中事实关系。

- [ ] **Step 4: 运行主讲版单元测试**

Run: `node --test tests/presentation_story_v2.test.mjs tests/presentation_layouts_v2.test.mjs tests/presentation_build_v2.test.mjs`  
Expected: PASS。

- [ ] **Step 5: 导出 15 页预览并生成 montage**

Run: `node scripts/build_presentation_v2.mjs --mode main --preview-only`  
Expected: `.presentation-build/v2/main-montage.png` 和 15 张页面 PNG 均存在。

- [ ] **Step 6: 逐页目检并修正溢出、重复版式和证据缩小问题**

必须检查标题、主图、辅助标注、业务结论、来源与状态；任何关键内容只能靠放大才能看清时，返回布局而不是继续缩字。

- [ ] **Step 7: 提交主讲版生成能力**

```bash
git add scripts/build_presentation_v2.mjs tests/presentation_build_v2.test.mjs
git commit -m "feat(presentation): build evidence-dense main deck"
```

### Task 4: 增加五页追问备份并导出最终 PPTX

**Files:**
- Modify: `scripts/build_presentation_v2.mjs`
- Modify: `tests/presentation_build_v2.test.mjs`
- Output: `docs/presentation/generated/星地智调_主讲稿_v2_高信息密度版.pptx`

**Interfaces:**
- Consumes: `BACKUP_SLIDES`、`buildMainDeck()`。
- Produces: `buildBackupDeck(presentation): Promise<void>`、`exportFinalDeck(): Promise<ValidationResult>`、20 页最终 PPTX。

- [ ] **Step 1: 扩展失败测试，锁定备份页顺序和默认路径边界**

测试断言 B1—B5 位于第 16—20 页，主讲目录和默认播放清单只包含 1—15 页，备份页标题明确标注“答辩备查”。

- [ ] **Step 2: 运行测试并确认失败**

Run: `node --test tests/presentation_build_v2.test.mjs`  
Expected: FAIL，提示备份页或默认路径元数据缺失。

- [ ] **Step 3: 实现五页备份页和最终导出**

备份页复用六类布局，但信息更偏向公式、边界、来源和问答防线；不得新增未经签核结论。

- [ ] **Step 4: 在首次正式编辑命令前标记一次演示文稿编辑操作**

Run from presentations skill directory:  
`node container_tools/mark_artifact_operation_started.mjs --operation-kind edit --expected-output-count 1 --output-format pptx`

该命令在整个 v2 制作中只能成功执行一次。

- [ ] **Step 5: 使用 bundled runtime 导出并运行 finalizer**

Run: `node scripts/build_presentation_v2.mjs --mode full`  
Expected: 20 页 draft、20 张预览、validation JSON 和最终 PPTX；finalizer 不报告越界、缺失图片、字体替换或空白页。

- [ ] **Step 6: 运行全部演示文稿测试**

Run: `node --test tests/presentation_design.test.mjs tests/report_master_figure_v4.test.mjs tests/presentation_story_v2.test.mjs tests/presentation_layouts_v2.test.mjs tests/presentation_build_v2.test.mjs`  
Expected: PASS。

- [ ] **Step 7: 提交最终演示文件**

```bash
git add scripts/build_presentation_v2.mjs tests/presentation_build_v2.test.mjs docs/presentation/generated/星地智调_主讲稿_v2_高信息密度版.pptx
git commit -m "feat(presentation): deliver evidence-dense competition deck"
```

### Task 5: 页面级复核与交付文档更新

**Files:**
- Modify: `docs/presentation/星地智调_PPT制作方案_2026-11-07.md`
- Create: `docs/presentation/星地智调_PPT逐页验收_v2_2026-11-08.md`
- Inspect: `docs/presentation/generated/星地智调_主讲稿_v2_高信息密度版.pptx`

**Interfaces:**
- Consumes: 20 页最终 PPTX、validation JSON、montage 和证据合同。
- Produces: 逐页验收记录，包含页码、主判断、证据路径、口径状态、目检结论和待替换项。

- [ ] **Step 1: 编写逐页验收清单**

对 1—20 页逐一记录标题、主证据、辅助证据、业务结论、来源、当前状态和是否通过。

- [ ] **Step 2: 在 PowerPoint 中打开最终文件并检查**

核验画布比例、字体、图像、中文换行、备注、页序、主讲/备份边界和静态可读性；只读检查，不修改事实内容。

- [ ] **Step 3: 更新制作方案的实施状态**

将 v2 路径、15＋5 页结构、Guard 边界和正式结果替换规则写入制作方案。

- [ ] **Step 4: 运行最终回归与差异检查**

Run: `node --test tests/presentation_design.test.mjs tests/report_master_figure_v4.test.mjs tests/presentation_story_v2.test.mjs tests/presentation_layouts_v2.test.mjs tests/presentation_build_v2.test.mjs`  
Run: `git diff --check`  
Expected: 全部 PASS，且无 whitespace error。

- [ ] **Step 5: 提交验收文档**

```bash
git add docs/presentation/星地智调_PPT制作方案_2026-11-07.md docs/presentation/星地智调_PPT逐页验收_v2_2026-11-08.md
git commit -m "docs(presentation): record v2 slide acceptance"
```

## Self-Review

- 设计文档 1—10 节均对应到 Task 1—5；15 页、5 页备份、六类版式、Guard 边界、四档口径和 PowerPoint 目检均有实施与验证步骤。
- 所有任务均形成独立可审查交付，先测试、再实现、再验证、再提交。
- `SlideSpec`、布局渲染器和生成入口的接口名称在前后任务中保持一致。
- 五项高风险输入均已分配到具体测试任务。
- 计划只决定接口、测试和验收，不抄写实现体。
