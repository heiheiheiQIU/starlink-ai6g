# 星地智调报告 v3 图文完整版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保持正式实验“未完成”口径和官方七章结构的前提下，将17页文字表格稿升级为包含10至13张核心图、规范图题与交叉引用、统一公式表格和完整参考文献的 v3 DOCX/PDF。

**Architecture:** `docs/report/report_v3.md` 作为唯一内容源；`scripts/build_report_docx.py` 负责 claim 门禁、Markdown 转 DOCX、图表公式编号和版式后处理；现有 v2 科研图的 SVG 作为正文内嵌资产和可编辑源。输出为 `星地智调_作品方案_v3.docx` 和用于视觉复核的同名 PDF。

**Tech Stack:** Markdown、Pandoc、python-docx、OOXML、SVG/PNG、Poppler、Word DOCX

**Spec:** `docs/materials/星地智调_三人统一图表生成任务书_2026-11-07.md`

## Global Constraints

- 正文保留10至13张核心图，图件使用统一 v2 科研视觉包。
- 不把开发期规则结果写成 AI 正式结果；正式结论保持“未完成”。
- 未签核 claim-A1、claim-X1/X2/X3、claim-R1 不得进入发布数字。
- 全篇不得出现单位、教师、成员姓名、联系方式或校徽。
- 作品简介保持300至500字；官方七章结构不变。
- A4，宋体小四正文，黑体标题，公式、表格、图题连续编号。
- PDF小于15MB，DOCX和PDF必须逐页渲染检查。

## Review Focus

- 图片过大造成空白页或图题跨页。
- 图内小字在A4宽度下不可读。
- 图题编号与正文引用不一致。
- 公式或表格编号因新增图件而错位。
- 图件包含开发期结果但正文误写为正式效果。

---

### Task 1: 图件清单与 Markdown 内容补全

**Files:**
- Create: `docs/report/report_v3.md`
- Test: `scripts/tests/test_build_report_docx.py`

**Interfaces:**
- Consumes: `docs/report/report_v2.md`、`docs/figures/generated/v2/previews/*.png`
- Produces: 12张带语义标签、图题和正文引用的 Markdown 主稿

- [x] **Step 1: 添加失败测试**

验证 report_v3 含12个 `fig:` 标签、所有图片路径存在、第11页结果口径仍为“未完成”、无待办或身份信息。

- [x] **Step 2: 复制并补全主稿**

在场景需求、总体架构、AI+6G、评分器、协议、能量、开发期证据、正式实验协议、产业价值和落地路线处插入核心图；删减与图重复的表述。

- [x] **Step 3: 运行内容门禁**

运行单元测试和材料门禁，确保待签核 claim 未被解析进入发布数字。

### Task 2: 图题、交叉引用与版式生成

**Files:**
- Modify: `scripts/build_report_docx.py`
- Modify: `scripts/tests/test_build_report_docx.py`
- Create: `docs/report/星地智调_作品方案_v3.docx`

**Interfaces:**
- Consumes: Task 1 的语义图标签与图片路径
- Produces: 连续 Figure SEQ、书签、REF 引用、固定图宽和图题样式

- [x] **Step 1: 添加失败测试**

验证图题解析、Figure SEQ书签、图引用替换和图片段落保持居中且与图题同页。

- [x] **Step 2: 实现图件后处理**

扩展生成器以识别 `fig:` 标签，统一图片宽度为正文版心，插入“图 N  标题”并建立交叉引用。

- [x] **Step 3: 生成 v3 DOCX**

使用捆绑Python和项目Pandoc生成文档，检查页数、图数、表数、公式数及字段。

### Task 3: 全文格式与内容终审

**Files:**
- Modify: `docs/report/report_v3.md`
- Regenerate: `docs/report/星地智调_作品方案_v3.docx`
- Create: `docs/report/星地智调_作品方案_v3.pdf`

**Interfaces:**
- Consumes: Task 2 的可渲染 DOCX
- Produces: 提交候选 DOCX/PDF

- [x] **Step 1: 渲染全部页面**

优先使用捆绑LibreOffice；若环境未提供，则用 Microsoft Word 本机导出 PDF，并使用捆绑 Poppler 生成逐页 PNG。

- [x] **Step 2: 逐页视觉检查**

检查封面、作品简介、所有图表公式、参考文献和附录；修复空白页、裁切、表格断裂和图题孤行。

- [x] **Step 3: 最终门禁**

验证匿名、claim状态、页数、PDF大小、DOCX结构、图片数量和引用完整性。

- [x] **Step 4: 本地提交**

仅提交 report_v3 源稿、生成器、测试、v3 DOCX/PDF和计划，不推送远端，不提交 Word 锁文件或渲染中间件。
