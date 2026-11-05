# 星地智调最终冲刺（材料与演示）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不伪造数据、不突破四档效果口径、不绕过三方验收的前提下，于 2026-11-12 20:00 前完成“星地智调”场景设计赛道的正式报告、PPT、演示视频、前端黄金演示链路和可审计发布包。

**Architecture:** 以“唯一叙事主线＋唯一事实源＋单一黄金演示路径”为核心。前端只展示仓库真实实现的算法与数据来源；报告、PPT和视频从同一 claim/证据矩阵生成；A/B交付只由C读取、复核和引用，任何需要三方签收的结论不得由DeepSeek代签。

**Tech Stack:** React 18、TypeScript 5.9、Vite 6、Vitest 2、Python 3.12、pytest、Markdown、Pandoc/Word（最终转换）、Git。

**Spec:** `../../GPT裁决交接文档_2026-11-05.md`、`docs/materials/GPT_review_handoff_2026-11-05.md`、`docs/materials/material_skeleton_v2_2026-11-04.md`、`../../Require/AI6G作品方案参考模板（场景设计）.docx`

## 0. DeepSeek必须先读的执行约束

### 0.1 你的身份与权限

你是成员C的执行助手，不是项目总负责人，不是成员A/B，也不是赛事评委。

你可以：

- 修改 `frontend/` 下的前端源码、测试和样式；
- 修改或新建 `docs/report/`、`docs/slides/`、`docs/video/`、`docs/materials/`、`docs/release/` 下的材料；
- 修改 `scripts/generate_claim_values.py`、`scripts/check_material_gate.py` 及其测试；
- 读取A/B的代码、验收、证据、运行结果并做独立复核；
- 为C生成审查清单、逐页脚本、逐镜头脚本和验收记录草稿。

你不可以：

- 擅自修改 `backend/contracts.py`、`configs/schema.json` 或公共API合同；
- 擅自重训、替换或宣称接受A的模型包；
- 擅自改写B的仿真、正式输入或统计结果；
- 用C的复核代替A/B回执，或写“三方通过”而缺少任一方正式记录；
- 把fixture、契约样例、开发期规则矩阵写成正式AI实验结果；
- 把“等效/负/未完成”改写成“提升”“领先”或“显著优于”；
- 写入学校、姓名、学号、指导老师姓名、绝对路径、个人账号、logo；
- 为了视觉效果编造模型归因百分比、链路参数、运行状态、run_id或实验数值；
- 删除历史证据、覆盖旧冻结包、重写他人的验收结论；
- 直接在 `main` 上开发或强推远端。

### 0.2 每一任务的强制工作法

每个任务都必须按以下顺序执行，不得跳步：

1. **读取**：先完整读取任务列出的输入文件，不得只看文件名或摘要。
2. **复述**：用5—10行写出当前事实、目标、禁止变化的接口。
3. **测试先行**：涉及代码行为时，先写失败测试并记录RED结果。
4. **最小修改**：只修改本任务必需文件，不顺手重构无关代码。
5. **验证**：执行定向测试、前端全测和构建；材料任务执行门禁和全文搜索。
6. **自审**：对照本计划的验收条件逐条打勾，不以“看起来可以”代替证据。
7. **交接**：输出“修改文件、验证命令、实际结果、剩余风险、建议提交信息”。

遇到失败时必须使用 systematic-debugging 思路：先复现、定位根因、写回归测试，再修复。禁止连续尝试多个猜测性改动。

声称“完成、修复、通过”前必须执行 verification-before-completion：引用本次刚运行的命令和输出，不得沿用历史测试数。

### 0.3 每次给C的固定回执格式

```markdown
## DS任务回执：<任务编号与名称>

- 固定基线：<完整SHA>
- 当前分支：<branch>
- 工作树状态：<clean/列出既有未提交文件>
- 实际修改：
  - `<path>`：<做了什么>
- 未修改的保护对象：
  - `backend/contracts.py`：SHA前缀 <...>
  - `configs/schema.json`：SHA前缀 <...>
- 验证：
  - `<命令>` → `<实际结果>`
- 数据来源标签：fixture / development_run / formal_run / verified_asset
- 四档结果口径：胜 / 等效 / 负 / 未完成 / 不适用
- 剩余风险：<没有则写“无”>
- 建议提交信息：`<type(scope): message>`
- 需要A/B/C谁签收：<明确列出，禁止写“大家”>
```

### 0.4 启动前门禁

- [ ] 在仓库根执行 `git status --short`，保存输出。
- [ ] 执行 `git branch --show-current`，必须是C的功能分支或隔离工作树，不得是`main`。
- [ ] 执行 `git rev-parse HEAD`，在回执中记录完整SHA。
- [ ] 记录既有未提交文件；不得覆盖或清理不属于本任务的改动。
- [ ] 阅读 `CONTRIBUTING.md`、`../../GPT裁决交接文档_2026-11-05.md`、本计划全文。
- [ ] 阅读 `docs/acceptance/` 中WP1、WP2、WP5和A-N4相关回执。
- [ ] 明确当前正式结果仍处于“未完成”时，不得在材料中提前填胜负数字。

## Global Constraints

- 内部提交截止：**2026-11-12 20:00（Asia/Shanghai）**。
- 官方截止：**2026-11-13**；不得用官方截止吞掉内部缓冲。
- 11月6日20:00后冻结功能、接口、模型和正式实验配置；之后只修阻断问题。
- 所有效果结论只允许：**胜、等效、负、未完成**。
- 正式输入为18工况×10轨迹，seed 200000—200179；与开发/训练seed必须隔离。
- 旧learned包和A-N4b首批均为零损失训练域；正式实验含随机丢失，属于域外评估。
- 报告/PPT/视频中的数字必须来自已签核claim；fixture数字必须显式标注“契约样例，非实验结果”。
- 报告、PPT、视频和前端不得出现身份信息。
- 官方模板要求作品简介300—500字；不得继续使用“≤300字”的旧口径。
- PDF必须小于10MB；视频按赛事最终核实的时长和大小限制执行。
- 前端必须通过70项现有测试基线、TypeScript检查和Vite生产构建；测试数随新增测试增加，不得下降。
- 禁止新增未经必要性论证的依赖；优先使用现有React/CSS/Vitest能力。
- 不以“视觉更炫”为由牺牲可读性、来源标签、错误状态或实验边界。

## Review Focus

1. **数据源混合**：同一页面同时存在fixture和真实运行时，每个面板必须有独立来源标记，不能用一个全局FIXTURE覆盖真实数据。
2. **服务离线**：后端未启动或轮询失败时，页面不得显示“运行服务已连接”，不得把旧结果伪装成在线结果。
3. **算法文案漂移**：前端和材料不得出现真实实现中不存在的VoI/bit、模型归因百分比、多路由选择或RUL直接参与评分。
4. **未签核数字**：pending、未知claim、残余占位、手写编号、身份信息中的任一项都必须阻止发布。
5. **四档负结果**：正式结果为等效、负或未完成时，报告/PPT/视频必须切换到对应叙事模板，而不是隐藏结果或临时改指标。

---

## 1. 当前冻结事实：DS不得自行改写

### 1.1 项目一句话

面向6G星地融合环境，在窗口、带宽、随机丢失、能量储备和任务期限约束下，由学习评分器对 `task × transmission_mode` 候选动作估值，再由约束解码器、Guard、ACK/重传协议形成可执行、可回退、可审计的健康感知遥测调度闭环。

### 1.2 真实算法边界

- learned输入为冻结 `policy-features-v1`：14个全局特征＋9个候选特征，共23维。
- 全局特征包括：仿真时间、缓存字节、能量/SOC/容量下界、任务数、inflight状态、下一窗口起点/持续时间、robust/fast速率与损失、是否存在窗口。
- 候选特征包括：idle/robust/fast标识、到达后时长、距期限时长、载荷、剩余字节、剩余比例、优先级。
- 模型输出候选动作分数；Guard负责窗口、能量、单在途、字节配额等硬约束。
- 教师效用是加权按时完整交付效用，不是已实现的“每bit信息价值”分解。
- 当前系统在单条星地链路上选择robust/fast模式，不是多卫星、多路由或网络切片路由算法。
- RUL没有进入当前23维评分特征；材料只能写“健康状态下界参与决策”，不能写“寿命预测直接决定调度”。

### 1.3 已签核与未签核

- 已验证：数据合同、模型包身份、Runner/API接入、错误回退、协议、开发期规则矩阵、前端功能和证据链。
- 未完成：A-N4b最终包、A对WP2的正式复验、正式900策略运行与统计、第三台机器验收、最终材料和视频。
- 正式结果没有签核前，唯一允许口径是“未完成”。

### 1.4 唯一叙事主线

全文只允许以下主线：

> 星上能量和星地链路窗口构成刚性约束，遥测任务价值、期限和数据量异构；本方案用学习评分器估计候选动作价值，用约束解码与协议闭环保证可执行性，以预登记配对实验裁决AI在不同工况下的收益与边界，并用run_id、哈希和三方验收实现可复现交付。

禁止另起“寿命预测平台”“卫星路由系统”“大模型智能体”“数字孪生”等第二主线。

---

## 2. 文件结构与交付物

本轮最终应形成以下文件；没有列出的新文件不得随意创建。

### 2.1 前端

- Modify: `frontend/src/App.tsx` — 根据页面显示正确的数据源横幅和DEMO时间标签。
- Modify: `frontend/src/components/AppSidebar.tsx` — 移除虚假的固定“服务已连接”。
- Modify: `frontend/src/components/FixtureBanner.tsx` — 改为可配置来源横幅。
- Create: `frontend/src/domain/dataSource.ts` — 页面级来源类型和文案唯一映射。
- Create: `frontend/src/domain/dataSource.test.ts` — 来源映射和禁用措辞回归。
- Modify: `frontend/src/domain/flow.ts` — 对齐真实23维特征、候选评分和传输模式。
- Modify: `frontend/src/domain/flow.test.ts` — 禁止VoI/bit、多路由、虚假归因文案。
- Modify: `frontend/src/components/StageExperience.tsx` — 删除伪归因百分比，展示真实输入类别与候选分数。
- Modify: `frontend/src/pages/FlowWorkspace.tsx` — hero文案改为“传什么、何时传、采用何种传输模式”。
- Modify: `frontend/src/components/RealRunPanel.tsx` — 增强数据源、在线/离线和历史结果状态。
- Modify: `frontend/src/components/RealRunPanel.test.tsx` — 状态与来源测试。
- Modify: `frontend/src/pages/MatrixPage.tsx` — 开发期规则矩阵边界、`value`拼写、配色与来源。
- Modify: `frontend/src/pages/MatrixPage.test.tsx` — 来源和禁用主张测试。
- Modify: `frontend/src/pages/EvidencePage.tsx` — 输入框样式和数据源说明一致。
- Modify: `frontend/src/styles/global.css` — 统一表单、来源徽标、对比度和演示态。
- Modify: `frontend/src/styles/tokens.css` — 只在必要时补充来源/状态颜色token。

### 2.2 材料治理

- Modify: `docs/materials/material_skeleton_v2_2026-11-04.md` — 官方模板口径修正。
- Modify: `docs/materials/claims_spec.json` — 补全可验证来源字段，保持pending真实状态。
- Modify: `scripts/generate_claim_values.py` — 校验signed_off条目完整性，不伪称直接解析证据。
- Modify: `scripts/check_material_gate.py` — 拒绝全部残余claim、未知claim、pending、身份信息和手写编号。
- Create: `tests/test_material_claims.py` — claim生成与门禁回归。
- Create: `docs/materials/CLAIM_EVIDENCE_MATRIX.md` — 主张、证据、失效边界、材料落点。
- Create: `docs/materials/DECISIONS.md` — 模型、数据、文案和四档结果决策日志。

### 2.3 最终材料源

- Create: `docs/report/星地智调_场景设计方案.md` — 唯一正式报告Markdown源。
- Create: `docs/report/FIGURE_PLAN.md` — 图表编号、来源、生成状态和材料落点。
- Create: `docs/slides/星地智调_PPT逐页脚本.md` — 10页以内的逐页设计和讲稿。
- Create: `docs/video/星地智调_演示脚本.md` — 3分30秒至4分30秒逐镜头脚本。
- Create: `docs/release/FINAL_RELEASE_CHECKLIST.md` — 最终提交清单。
- Create: `docs/acceptance/C_materials_demo_final_2026-11-11.md` — C最终复核回执草稿，只有C本人确认后才能改为accepted。

---

### Task 1: 修正前端数据来源、服务状态和算法文案

**Deadline:** 2026-11-06 12:00

**Files:**
- Create: `frontend/src/domain/dataSource.ts`
- Create: `frontend/src/domain/dataSource.test.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/AppSidebar.tsx`
- Modify: `frontend/src/components/FixtureBanner.tsx`
- Modify: `frontend/src/domain/flow.ts`
- Modify: `frontend/src/domain/flow.test.ts`
- Modify: `frontend/src/pages/FlowWorkspace.tsx`
- Modify: `frontend/src/components/StageExperience.tsx`

**Interfaces:**
- Produces: `DataSourceKind = 'fixture' | 'mixed' | 'development_run' | 'formal_run' | 'verified_asset'`
- Produces: `PageDataSource { kind; badge; title; description; source }`
- Produces: `getPageDataSource(page: PageId): PageDataSource`
- Consumes: `PageId` from `frontend/src/domain/navigation.ts`

- [ ] **Step 1: 写数据来源映射失败测试**

测试必须断言：

- `flow`为fixture；
- `compare`为mixed；
- `matrix`为development_run，source含`R5_2026-10-29/per_run.csv`；
- `evidence`为mixed；
- 不得把matrix描述为“正式AI实验”；
- 任一来源对象必须同时提供badge、description和source。

- [ ] **Step 2: 运行定向测试确认RED**

Run:

```powershell
Push-Location frontend
& .\node_modules\.bin\vitest.cmd run src/domain/dataSource.test.ts
Pop-Location
```

Expected: FAIL，因为`dataSource.ts`尚不存在。

- [ ] **Step 3: 实现页面级来源映射**

固定映射：

| 页面 | kind | 必须显示的边界 |
|---|---|---|
| flow | fixture | 契约样例，只演示端到端机制 |
| overview | mixed | 项目状态汇总，含已验证事实与待完成事项 |
| assistant | verified_asset | 只回答本地证据可支持内容 |
| compare | mixed | 上部可发真实run，下部默认契约样例 |
| matrix | development_run | B R5开发期规则运行，非正式AI实验 |
| evidence | mixed | fixture状态语义＋真实run恢复入口 |
| assets | verified_asset | 资产身份和来源，不代表模型效果 |

- [ ] **Step 4: 让`FixtureBanner`接收来源对象**

接口固定为：

```ts
interface FixtureBannerProps {
  source: PageDataSource
}
```

组件名称可保留以减少改动，但UI不得所有页面都显示FIXTURE。

- [ ] **Step 5: 修正全局状态与时间标签**

- `AppSidebar.tsx`把“运行服务已连接”改为中性事实“演示工作台”；副标题“服务状态见运行面板”。
- 不新增虚假健康检查，不把在线状态写死。
- `App.tsx`把`OBS · 2026-10-29T15:00Z`改为`DEMO OBS · 2026-10-29T15:00Z`。

- [ ] **Step 6: 写算法文案禁止项测试**

测试读取`FLOW_STEPS`并断言评分步骤文本不包含：

- `VoI / bit`
- `信息新鲜度`
- `不确定性`
- `走哪条链路`
- `风险权重`、`能耗影响`作为模型归因百分比

同时必须包含：

- `23维`
- `task × mode`或等价中文
- `能量/SOC/容量下界`
- `窗口速率与丢失`
- `期限、剩余字节和优先级`
- `约束解码`或`Guard`

- [ ] **Step 7: 修正流程文案**

评分步骤采用以下事实口径，不得自由扩写：

```text
学习评分器读取能量/SOC/容量下界、下一窗口速率与丢失、任务期限、剩余字节和优先级等23维公开特征，对task×mode候选动作给出分数；硬约束由下一步解码器和Guard检查。
```

主舞台hero改为：

```text
以保守健康状态为输入，让AI在6G星地链路约束下决定“传什么、何时传、采用何种传输模式”。
```

- [ ] **Step 8: 删除三项伪归因百分比**

`StageExperience.tsx`不得再显示“风险权重92%/期限紧迫度95%/能耗影响55%”。替换为：

- 输入特征组：健康下界、窗口状态、任务状态、模式标识；
- 候选动作：`T-101 × robust`、`T-101 × fast`、`idle`；
- 输出：候选分数，并明确“契约样例分数，非模型解释归因”。

特征数字必须来自现有fixture对象；若没有可靠值，只显示字段名和“已输入”，不得新编数值。

- [ ] **Step 9: 运行定向与全量前端验证**

Run:

```powershell
Push-Location frontend
& .\node_modules\.bin\vitest.cmd run src/domain/dataSource.test.ts src/domain/flow.test.ts src/pages/FlowWorkspace.test.tsx src/App.test.tsx
& .\node_modules\.bin\vitest.cmd run
& .\node_modules\.bin\tsc.cmd --noEmit
& .\node_modules\.bin\vite.cmd build
Pop-Location
```

Expected: 全部通过；总测试数不得低于当前70项。

- [ ] **Step 10: 提交建议**

```text
fix(frontend): align demo sources and AI scoring claims
```

**Acceptance:** C复核；涉及算法事实的文案由A只做事实核对，不要求A批准视觉设计。

---

### Task 2: 统一真实运行控件和实验矩阵视觉

**Deadline:** 2026-11-06 18:00

**Files:**
- Modify: `frontend/src/components/RealRunPanel.tsx`
- Modify: `frontend/src/components/RealRunPanel.test.tsx`
- Modify: `frontend/src/pages/MatrixPage.tsx`
- Modify: `frontend/src/pages/MatrixPage.test.tsx`
- Modify: `frontend/src/pages/EvidencePage.tsx`
- Modify: `frontend/src/styles/global.css`
- Modify: `frontend/src/styles/tokens.css` only if existingtokens不足

**Interfaces:**
- Consumes: existing `RunController`
- Produces: no backend/API/schema changes
- Preserves: `RunSourceBadge` semantics and `useRun` state machine

- [ ] **Step 1: 为运行面板补来源与状态测试**

必须覆盖：

- 离线时显示“未连接服务”，不显示“已连接”；
- completed且有结果时显示真实run_id和`ONLINE RUN`来源；
- 参数改变后旧结果显示“历史展示”；
- failed不得显示最终指标；
- fixture表格与真实结果不得共用同一来源徽标。

- [ ] **Step 2: 统一表单控件**

所有`select/input/button`必须：

- 使用暗色背景、清晰边框、统一高度；
- 标签在控件上方或左侧留有至少8px间距；
- 有`:focus-visible`焦点环；
- disabled状态可辨认；
- 1440×900下不挤在一行，最小宽度时可换行；
- 不使用浏览器默认白底控件。

- [ ] **Step 3: 修正矩阵事实与拼写**

- `EDF=vale`改为`EDF/value规则基线`。
- hero增加“开发期真实规则运行，非正式AI实验”。
- 保留R5来源路径和360 policy-runs事实。
- 不把learned未接入写成“自动扩展”；改为“正式learned结果签核后再扩展”。

- [ ] **Step 4: 调整热力图可达性**

- 不只依赖红—绿区分；保留数字标签并使用蓝—橙或明度连续色阶。
- 对比度满足深色背景下可读；禁止高饱和荧光大面积铺满。
- 颜色函数必须有0、0.5、1三个测试点。

- [ ] **Step 5: 视觉回归人工检查**

在1440×900和1920×1080分别检查：

- 方案对比首屏；
- 实验矩阵首屏和完整热力图；
- 证据链输入区；
- 主舞台AI评分步骤；
- 主舞台发送/确认步骤。

记录截图文件名、viewport和HEAD SHA到`docs/evidence/C/frontend_visual_2026-11-06/README.md`；若不提交截图，至少提交截图索引和人工检查表。

- [ ] **Step 6: 验证**

Run同Task 1全量前端验证。Expected: 全部通过，构建产物无错误，浏览器控制台无error/warn。

- [ ] **Step 7: 提交建议**

```text
fix(frontend): polish run controls and matrix provenance
```

**Acceptance:** C视觉签收；B只确认真实run状态和字段没有被误读。

---

### Task 3: 修复claim生成与材料发布门禁

**Deadline:** 2026-11-06 18:00

**Files:**
- Modify: `docs/materials/claims_spec.json`
- Modify: `scripts/generate_claim_values.py`
- Modify: `scripts/check_material_gate.py`
- Create: `tests/test_material_claims.py`
- Modify: `docs/materials/material_skeleton_v0_2026-11-04.md` — 仅增加历史版本停用提示。
- Modify: `docs/materials/material_skeleton_v1_2026-11-04.md` — 仅增加历史版本停用提示。
- Modify: `docs/materials/material_skeleton_v2_2026-11-04.md`

**Interfaces:**
- Produces: `validate_claims(spec: dict) -> list[str]`
- Produces: `scan_material_text(path: Path, text: str, claims: dict) -> list[str]`
- Output: `docs/report/claim_values.json`

- [ ] **Step 1: 写门禁失败测试**

至少包含以下测试：

```text
test_gate_rejects_any_remaining_claim_placeholder
test_gate_rejects_pending_claim_reference
test_gate_rejects_unknown_claim_reference
test_gate_rejects_handwritten_figure_after_chinese_prefix
test_gate_rejects_windows_absolute_path
test_gate_rejects_identity_terms_from_config
test_generator_rejects_signed_off_claim_without_value_source_scope_hash
test_generator_keeps_pending_value_null
```

特别验证`见表3`、`如图4所示`均被拦截。

- [ ] **Step 2: 运行测试确认RED**

```powershell
py -3 -m pytest tests/test_material_claims.py -q
```

- [ ] **Step 3: 补全claim字段纪律**

所有`signed_off`条目必须含：

- `value`
- `unit`
- `source`
- `hash`
- `scope`
- `status: signed_off`

所有`pending`条目的`value`必须为`null`；不得提前填预测值。

`source`必须指向仓库相对路径或权威URL，禁止只写“B证据”“已复核”等不可定位文本。

- [ ] **Step 4: 修正生成器的诚实口径**

当前生成器只是从registry生成展示值，不是直接从所有verification文件自动抽取。代码注释和材料统一改为：

```text
claim registry是唯一材料数值源；signed_off条目必须绑定证据路径、哈希和验收状态。生成器验证registry并生成材料值文件，不声称替代三方验收。
```

不得为了符合旧文案而实现脆弱的全仓库自动抓数。

- [ ] **Step 5: 修正门禁**

门禁必须拒绝：

- 任意`{{claim-*}}`残留，无论signed_off或pending；
- 引用不存在的claim；
- pending claim被渲染为数字；
- `TODO`、`待填`、`待签核`、`Pending`；
- 手写`图3/表3/见表3/如图3所示`；
- 绝对路径、已知身份词和logo引用；
- 报告目录不存在或没有Markdown文件。

- [ ] **Step 6: 修正官方模板冲突**

在`material_skeleton_v2_2026-11-04.md`中明确：

- 作品简介为300—500字；
- 官方一级结构为作品简介、一场景概述、二方案主体、三附录；
- 正文≤30页不是当前已证实硬约束，删除或标为待核实；
- 采用自动编号，删除v1中手写公式编号的冲突说明。

在v0、v1文件首部只增加醒目的`SUPERSEDED`提示，指向v2并说明其中“≤300字”不再有效；保留历史正文，不回写成当前事实。

- [ ] **Step 7: 验证**

```powershell
py -3 -m pytest tests/test_material_claims.py -q
py -3 scripts/generate_claim_values.py
py -3 scripts/check_material_gate.py docs/report docs/materials/claims_spec.json
```

注意：正式报告尚未创建时，最后一条预期可以因目录无MD失败；Task 4创建报告后必须转绿。不得把这个预期失败写成“全部通过”。

- [ ] **Step 8: 提交建议**

```text
fix(materials): enforce evidence-bound claims and release gate
```

**Acceptance:** C签收；若改动任何A/B结果值，必须由对应成员复核。

---

### Task 4: 建立正式报告源和主张—证据矩阵

**Deadline:** 2026-11-07 12:00完成无正式结果完整稿；正式结果签核后4小时内填充

**Files:**
- Create: `docs/report/星地智调_场景设计方案.md`
- Create: `docs/report/FIGURE_PLAN.md`
- Create: `docs/materials/CLAIM_EVIDENCE_MATRIX.md`
- Create: `docs/materials/DECISIONS.md`

**Interfaces:**
- Consumes: `docs/report/claim_values.json`
- Consumes: A/B/C正式验收文件和WP5统计结果
- Produces: report source used by PPT/video, not a parallel facts system

- [ ] **Step 1: 按官方模板创建报告结构**

固定结构：

```markdown
# 作品简介（300—500字）
# 一、场景概述
## （一）场景名称
## （二）场景背景与真实业务需求
## （三）问题定义、对象与边界
# 二、场景设计方案
## （一）总体架构与端到端闭环
## （二）6G星地链路与业务约束建模
## （三）健康感知学习评分器
## （四）约束解码、Guard与协议执行
## （五）仿真、数据与实验设计
## （六）实验结果与四档裁决
## （七）前端演示、工程部署与推广价值
## （八）创新点、局限与后续路线
# 三、附录
## 附录A 数据字典与参数
## 附录B 复现与交付清单
## 附录C 主张—证据索引
```

- [ ] **Step 2: 写作品简介**

作品简介必须300—500字，顺序固定：

1. 两句真实业务问题；
2. 一句总体方案；
3. 三项贡献，每项一句；
4. 一句正式实验四档结论；
5. 一句落地与推广价值。

正式结果未签核时第四项写“正式配对实验按预登记方案执行中”，不得预填收益。

- [ ] **Step 3: 写评委可理解的6G逻辑链**

必须画清并写清：

```text
健康状态下界 + 遥测任务
        ↓
6G星地窗口/速率/丢失状态
        ↓
AI对task×mode候选动作评分
        ↓
约束解码/Guard
        ↓
robust/fast/idle执行
        ↓
ACK、超时、重传、去重
        ↓
按时完整交付率/能耗/回退率
        ↓
run_id + 哈希 + 三方验收
```

禁止把寿命预测写成主算法；它是健康状态来源背景，当前正式调度使用的是公开健康下界。

- [ ] **Step 4: 固定三项创新，不再增删**

创新1：健康状态与6G链路联合进入候选动作评分，而非只按期限或优先级排序。

创新2：学习评分与约束执行解耦，AI负责排序，Guard和协议保证窗口、能量、单在途和重传义务。

创新3：从输入、模型、随机信道到事件和结果的证据链，支持四档诚实裁决和失败回放。

每项创新必须附“现有不足—本方案机制—验证证据—失效边界”。

- [ ] **Step 5: 构建主张—证据矩阵**

每行字段固定：

```text
claim_id | 主张原文 | 状态 | 证据路径 | SHA/run_id | 验收人 | 可支持 | 不可支持 | 报告位置 | PPT页 | 视频时间
```

至少覆盖政策、协议能量、数据审计、模型小样本、WP2回退、开发期规则矩阵、正式总体结果、分工况结果、失败案例、换机复现。

- [ ] **Step 6: 写四档结果模板**

报告中预置以下四段，只在最终版保留一段：

**胜：** 仅在配对区间支持时写“在冻结合成域外压力测试的指定工况中，learned相对规则基线获得正向配对差”；不得扩展到真实在轨性能。

**等效：** 写“总体未观察到稳定优势，但学习评分器在受控回退下没有破坏安全约束；结果明确了无需启用AI的工况范围”。

**负：** 写“域外随机丢失下learned低于规则基线，说明零损失训练域不足；系统的价值在于可回退架构、失效边界识别和下一轮数据设计依据”。

**未完成：** 写“截至材料冻结时正式实验未形成三方签核，本文只报告工程闭环与开发期验证，不给出AI收益数字”。

- [ ] **Step 7: 建立图表计划**

`FIGURE_PLAN.md`至少包含：

| 图 | 内容 | 数据来源 | 必要性 |
|---|---|---|---|
| 图1 | 真实业务场景与矛盾 | 官方/自绘，不含虚假指标 | 建立需求 |
| 图2 | 端到端闭环架构 | 仓库接口 | 讲清系统 |
| 图3 | 评分—解码—执行关系 | 真实算法 | 回答AI+6G |
| 图4 | 共享随机信道与协议 | B实现 | 公平性 |
| 图5 | 数据/训练/正式域边界 | A审计+WP5 | 诚实边界 |
| 图6 | 正式实验矩阵 | WP5签核结果 | 核心结果 |
| 图7 | 胜平负条件图 | WP5统计 | 回答适用性 |
| 图8 | 失败或回退事件链 | 指定run | 可信AI |
| 图9 | 前端黄金路径 | 实际截图 | 工程落地 |
| 图10 | 复现与证据链 | acceptance/evidence | 推广价值 |

不为凑页数添加装饰图。所有图必须回答一个评委问题。

- [ ] **Step 8: 写决策日志**

`DECISIONS.md`至少记录：

- 新旧模型包选择及截止线；
- 是否存在成熟优化器对照；
- 正式结果四档；
- CAICT引用保留或删除；
- fixture/开发期/正式结果分类；
- 视频使用直播还是签核run回放；
- 任何上游数字变化对报告/PPT/视频的影响。

- [ ] **Step 9: 材料自审**

逐段检查：

- 每个技术名词在前文定义；
- 每个数字有claim或明确来源；
- 每个“提升/更优/显著”有统计依据；
- 每个局限写明影响，不写空泛“未来研究”；
- 正文不出现代码堆砌、测试数堆砌和SHA长串；细节放附录；
- 报告开头两页能让非算法评委看懂需求、方案和价值。

- [ ] **Step 10: 提交建议**

```text
docs(report): draft evidence-bound scene design solution
```

**Acceptance:** C主审；A核对算法与数据章；B核对仿真、协议和正式实验章；三方不允许互相代签。

---

### Task 5: 接收正式实验并执行四档裁决

**Deadline:** 2026-11-07 20:00

**Files:**
- Modify: `docs/materials/claims_spec.json`
- Modify: `docs/report/星地智调_场景设计方案.md`
- Modify: `docs/materials/CLAIM_EVIDENCE_MATRIX.md`
- Modify: `docs/materials/DECISIONS.md`
- Read only: B正式实验、统计和A/C验收文件

**Interfaces:**
- Consumes: B正式结果bundle、bootstrap/配对统计、manifest、运行清单
- Produces: one and only one of 胜/等效/负/未完成

- [ ] **Step 1: 核对正式运行身份**

必须确认：

- 恰有18工况×10独立输入；
- 三策略若全部执行，运行数口径解释清楚；
- seed为200000—200179；
- 同一trajectory的策略输入哈希一致；
- 模型manifest与冻结决策一致；
- 没有把重复EDF计为额外独立样本；
- failed run没有进入最终均值；缺失处理规则预先登记。

- [ ] **Step 2: 核对统计输出**

至少包含：

- 总体配对差；
- 分工况配对差；
- 区间或bootstrap结果；
- 回退率及原因；
- 安全违例数；
- 推理延迟；
- 失败运行清单；
- 域外限制声明。

- [ ] **Step 3: 应用四档规则**

不得由DeepSeek临时发明阈值。使用B预登记规则；若预登记文件没有明确阈值，状态保持“未完成”，先要求B补充裁决规则并由A/C复核。

- [ ] **Step 4: 更新claim但不得代签**

只有当对应验收文件存在且状态为accepted/signed_off时，才能把`claim-X1/X2/X3`从pending改为signed_off。

更新时必须填写：value、unit、source、hash、scope和acceptance路径。

- [ ] **Step 5: 反向影响复核**

按顺序检查：

```text
正式证据 → claims_spec → claim_values → 图表 → 报告正文 → 作品简介 → PPT → 视频旁白
```

任一层不一致则不允许进入发布候选。

**Acceptance:** A/B/C三方对各自范围签收。DeepSeek只整理，不作最终效果裁决人。

---

### Task 6: 制作10页以内的PPT逐页脚本

**Deadline:** 2026-11-09 20:00初稿；11月11日12:00终稿

**Files:**
- Create: `docs/slides/星地智调_PPT逐页脚本.md`

**Interfaces:**
- Consumes: formal report and claim matrix
- Produces: slide title, one-sentence claim, visual, evidence, speaker notes

- [ ] **Step 1: 使用固定10页结构**

1. 封面：项目名＋一句话价值，不含身份。
2. 真实业务痛点：为什么星地遥测不能“全传”。
3. 场景与约束：窗口、丢失、能量、任务价值。
4. 总体闭环：健康状态→AI评分→Guard→传输→证据。
5. AI+6G核心：23维公开特征、task×mode评分、robust/fast/idle。
6. 协议与可信工程：ACK、重传、回退、模型身份。
7. 实验设计：18×10、配对seed、域外限制、基线。
8. 正式结果：只显示四档签核结论和一张主图。
9. 前端与落地：黄金路径截图＋部署/推广。
10. 总结：三项贡献、边界、下一步。

- [ ] **Step 2: 每页限制**

- 标题≤16字；
- 一页只讲一个判断；
- 正文不超过5个要点，每点不超过18字；
- 只放1个主视觉或1组紧密关联图；
- 页脚写证据编号，不放长路径；
- 讲稿控制20—35秒；
- 不把报告表格缩小后直接贴入PPT。

- [ ] **Step 3: 结果页四档切换**

在脚本中保留四个候选版本，最终只启用已签核版本。等效/负/未完成版本必须同样完整，禁止把结果页删掉。

- [ ] **Step 4: 演讲追问准备**

脚本末尾附15个评委问题及30秒回答，至少包括：

- 为什么需要AI？
- AI没有增益怎么办？
- 这和6G有什么关系？
- 为什么不是普通卫星调度？
- 寿命预测到底用了没有？
- 是否使用真实卫星数据？
- 零损失训练为何测试随机丢失？
- 线性模型优于MLP如何解释？
- 如何保证AI不违反能量约束？
- 为什么没有成熟优化器？
- 前端数字是否真实？
- 如何复现？
- 如何推广到多星？
- 当前方案最大局限是什么？
- 三人团队如何完成工程闭环？

**Acceptance:** C和指导老师审看；算法回答由A复核，协议回答由B复核。

---

### Task 7: 制作黄金演示视频逐镜头脚本

**Deadline:** 2026-11-09 12:00脚本；11月10日18:00可审视频

**Files:**
- Create: `docs/video/星地智调_演示脚本.md`

**Interfaces:**
- Consumes: signed-off report/PPT/frontend build
- Produces: 3:30—4:30 video timeline and capture checklist

- [ ] **Step 1: 固定黄金路径**

视频不平均游览七个页面，只走：

```text
任务进入 → 窗口/链路状态 → AI候选评分 → Guard解码 → GW/SAT发送与ACK → 结果 → run_id证据
```

- [ ] **Step 2: 固定时间线**

| 时间 | 画面 | 旁白任务 |
|---|---|---|
| 0:00—0:25 | 场景痛点＋标题 | 解释为什么不能全传 |
| 0:25—0:55 | 总体架构图 | 说清AI与6G接口 |
| 0:55—1:35 | 流程1—3 | 任务、窗口、23维候选评分 |
| 1:35—2:10 | 流程4—5 | Guard、robust/fast、ACK重传 |
| 2:10—2:45 | 方案对比/矩阵 | 四档正式结果与域外边界 |
| 2:45—3:20 | 证据链 | run_id、哈希、回退和复现 |
| 3:20—3:50 | 总结 | 三项贡献与推广价值 |

如赛事最终要求更长，可增加评估方法，不增加无关页面漫游。

- [ ] **Step 3: 录制来源规则**

- 真实run必须显示run_id和ONLINE/FORMAL来源；
- 离线签核run回放必须显示“已签核运行回放”；
- fixture必须显示“契约样例，非实验结果”；
- 不隐藏失败、回退和域外声明；
- 页面动效完成后至少等待1秒再截图或切镜，避免CountUp中间值被录入；
- GW、数据块和SAT必须在同一链路轨迹上；ACK返回方向清楚；
- 光标移动有目的，不来回晃动；
- 画面不出现桌面通知、用户名、绝对路径或浏览器账号。

- [ ] **Step 4: 录制前检查**

- 使用1440×900或1920×1080固定分辨率；
- 浏览器缩放100%；
- 后端和前端版本SHA记录；
- 清理控制台错误；
- 预跑完整黄金路径两次；
- 旁白中的每个数字能定位claim；
- 准备直播失败时的签核回放方案。

**Acceptance:** C视觉/旁白主审；A/B分别核对算法和协议事实。

---

### Task 8: 第三台机器复现与演示彩排

**Deadline:** 2026-11-08 20:00

**Files:**
- Create: `docs/acceptance/third_machine_reproduction_2026-11-08.md`
- Modify: `docs/materials/claims_spec.json` only after C签收

- [ ] **Step 1: 在第三台RTX4060电脑从干净检出开始**

记录：OS、Node、pnpm、Python、Git SHA、安装命令和耗时。

- [ ] **Step 2: 复跑后端和前端发布门禁**

至少执行仓库README规定的后端全量、前端全量与构建。若依赖历史资产，记录恢复方法，不把本机绝对路径写进报告。

- [ ] **Step 3: 复跑一个规则run和一个learned run**

记录run_id、输入哈希、模型哈希、结果摘要、ZIP校验和和任何差异。

- [ ] **Step 4: 完整彩排视频黄金路径**

由非主要前端开发成员操作；记录卡住的步骤、误解点和总时长。

- [ ] **Step 5: 回执边界**

换机成功只支持“复现与部署链路可用”，不支持“算法在真实星上有效”。

**Acceptance:** 操作人签名可用成员代号A/B/C，不写真实姓名；C复核后才签核`claim-R1`。

---

### Task 9: 行政、匿名和最终发布门禁

**Deadline:** 2026-11-11 18:00完成预发布；11月12日18:00完成最终包

**Files:**
- Create: `docs/release/FINAL_RELEASE_CHECKLIST.md`
- Create: `docs/acceptance/C_materials_demo_final_2026-11-11.md`

- [ ] **Step 1: 行政状态必须人工确认**

清单至少包含：报名状态、团队信息、赛道、作品名、指导老师信息在系统中的状态、材料格式、视频格式、提交入口和截止时间。

这些信息只写“已由C在报名系统确认/待确认”，不得把身份信息抄入匿名作品。

- [ ] **Step 2: 全仓匿名搜索**

搜索：学校名、成员姓名、学号、邮箱、手机号、`C:\Users`、`D:\`、微信路径、logo文件和GitHub个人信息。

命中后先判断是否属于不提交的内部证据；最终提交目录必须零命中。

- [ ] **Step 3: 执行材料门禁**

```powershell
py -3 scripts/generate_claim_values.py
py -3 scripts/check_material_gate.py docs/report docs/materials/claims_spec.json
```

Expected: exit code 0，零占位、零pending引用、零身份、零手写编号。

- [ ] **Step 4: 执行代码门禁**

```powershell
Push-Location frontend
& .\node_modules\.bin\vitest.cmd run
& .\node_modules\.bin\tsc.cmd --noEmit
& .\node_modules\.bin\vite.cmd build
Pop-Location
```

后端使用B最终冻结回执中的准确命令，不自行缩小范围。

- [ ] **Step 5: 文件级检查**

- PDF可打开、目录正确、字体和公式无乱码；
- PDF小于10MB；
- 作品简介300—500字；
- 官方提示框已删除；
- PPT无身份、数字与报告一致；
- 视频可完整播放、时长/大小合规、字幕清晰；
- 源码/附件/支撑材料命名符合通知；
- 提交包内没有`.git`、`node_modules`、本地runs、缓存和个人临时文件。

- [ ] **Step 6: 三方终审**

- A：算法、训练、模型、数据边界；
- B：仿真、协议、正式结果、复现命令；
- C：报告、PPT、视频、前端、匿名和行政。

任何一方未完成对应范围时，回执写“未完成”，不得由DeepSeek代勾。

- [ ] **Step 7: C最终回执草稿**

回执必须列出：最终SHA、报告哈希、PPT哈希、视频哈希、前后端测试结果、材料门禁结果、四档效果结论、已知局限和提交时间。

DeepSeek只能写`ready_for_C_review`；只有C本人确认后才能改成`accepted`。

---

## 3. 三人最终分工与交接接口

### 成员A：数据与AI

交付给B/C：

- 新旧模型选择建议和固定SHA；
- 数据集manifest、划分、标签审计；
- 模型五文件和模型卡；
- WP2复验回执；
- 正式结果中模型行为、回退和适用域解释；
- 报告第“健康感知学习评分器”小节事实核对。

最后期限：11月6日18:00完成模型与WP2签收；否则走旧包或标记未完成。

### 成员B：仿真、API与正式实验

交付给A/C：

- 冻结正式输入和模型身份；
- 900策略运行或最终登记口径；
- 配对统计、区间、分工况结果、回退率、失败清单；
- 正式结果bundle、manifest、SHA和复现命令；
- 报告中协议、实验设计与结果章节事实核对。

最后期限：11月7日20:00完成正式结果候选；未签核则材料使用“未完成”。

### 成员C：前端、报告、PPT、视频与队长门禁

责任：

- 执行本计划Task 1—4、6—9；
- 不替A/B出具技术回执；
- 维护claim、材料主线、前端来源标签和最终提交；
- 组织三方终审和指导老师审看。

### 交接协议

任何交付必须同时包含：

```text
branch + full SHA + artifact paths + test command + actual result + evidence path + limitations + requested reviewer
```

仅有聊天摘要、截图或“我已完成”不构成交付。

---

## 4. 时间与工时分配

成员C有效工时建议：

| 类别 | 占比 | 停止线 |
|---|---:|---|
| 报告 | 33% | 11月11日12:00冻结正文 |
| PPT | 17% | 11月11日12:00冻结 |
| 视频 | 15% | 11月10日18:00可审版，11日修订 |
| 前端与联调 | 25% | 11月8日20:00后只修阻断 |
| 行政与发布 | 10% | 每日检查，11月12日优先级最高 |

每日结束时DeepSeek必须生成次日首要三项，不得同时开启超过两个未完成任务。

---

## 5. P0/P1/P2优先级

### P0：不完成就不能发布

1. 前端算法文案与真实实现对齐。
2. 数据来源和服务状态不自相矛盾。
3. 新旧模型按截止线裁决并保留三方门禁。
4. 正式结果四档签核，不越档。
5. 报告按官方结构和300—500字简介执行。
6. 材料零身份、零pending数字、零fixture冒充。
7. 报告/PPT/视频成品齐全且可打开。

### P1：显著影响得分

1. 真实运行控件视觉统一。
2. 单一黄金演示路径完整。
3. 图表优先、页面重点清晰。
4. 评委问答准备充分。
5. 第三台机器复现和演示彩排。

### P2：有余力再做

1. 非关键微动效；
2. 额外页面；
3. 新图标系统；
4. 与主线无关的动画或装饰；
5. 新模型架构探索。

P0未清零时禁止开始P2。

---

## 6. DeepSeek自检问题

每次提交前逐条回答，任一回答“不确定”即停止并查证：

1. 我写的每个数字来自哪个文件、run_id或权威来源？
2. 该数字是fixture、开发期结果还是正式结果？
3. 对应claim是否signed_off？谁签的？
4. 我是否把单星单链路的robust/fast写成了多路由或网络切片？
5. 我是否暗示RUL直接进入当前评分器？
6. 我是否把教师WOT效用写成未经实现的VoI/bit？
7. 我是否把模型候选分数写成可解释归因百分比？
8. 我是否把C复核写成三方验收？
9. 我是否隐藏等效、负结果或失败run？
10. 我是否写入身份、绝对路径或个人账号？
11. 我是否运行了本次修改对应的定向测试和全量验证？
12. 当前工作树里是否有不属于我的改动？
13. 我是否为了“看起来高级”增加了评委无法在30秒内理解的内容？
14. 报告、PPT、视频和前端是否在讲同一条主线？
15. 如果评委追问“依据在哪”，我能否在30秒内指出证据路径？

---

## 7. 完成定义

本计划只有在以下全部成立时才算完成：

- [ ] 前端算法文案与仓库真实实现一致；
- [ ] 页面数据来源和在线状态真实、清楚、不矛盾；
- [ ] 前端全测和构建通过，测试数不低于70；
- [ ] claim生成和材料门禁有回归测试；
- [ ] 官方模板冲突已修正；
- [ ] 正式报告Markdown完整；
- [ ] PPT逐页脚本完整并经指导老师审看；
- [ ] 视频逐镜头脚本和可审视频完成；
- [ ] 正式结果只有一个四档结论，且有对应签核；
- [ ] 第三台机器复现完成或如实标记未完成；
- [ ] 最终PDF/PPT/视频通过匿名、大小、格式和claim一致性检查；
- [ ] A/B/C各自范围有明确回执；
- [ ] C最终回执状态由C本人确认，不由DeepSeek代签；
- [ ] 工作树无未解释改动，最终候选SHA和各材料哈希已记录。

## 8. 执行顺序（不得自行调换）

```text
Task 1 前端真实性对齐
  → Task 2 视觉与来源统一
  → Task 3 claim/门禁修复
  → Task 4 报告无结果完整稿
  → Task 5 正式结果四档落位
  → Task 8 换机复现
  → Task 7 视频
  → Task 6 PPT
  → Task 9 最终发布
```

Task 4可以与A/B的算法和实验工作并行，但Task 5必须等待A/B正式交付；Task 6/7可以在Task 4后并行准备无数字版本，最终数字只能在Task 5签核后填入。Task 8按日期优先于PPT/视频终稿，不得因材料排版跳过换机验收。

## 9. 给DeepSeek的第一条执行指令

将下面内容原样发给DeepSeek，并附上本文件：

```text
你现在是“星地智调”项目成员C的受限执行助手。请完整读取：
1. docs/superpowers/plans/2026-11-05-ds-final-sprint-materials-demo.md
2. ../../GPT裁决交接文档_2026-11-05.md
3. docs/materials/GPT_review_handoff_2026-11-05.md

先不要修改任何文件。先执行本计划0.4启动前门禁，并按0.3格式输出基线回执；然后只执行Task 1。必须测试先行，不得顺手执行Task 2，不得修改backend合同、A模型或B仿真。完成Task 1后停下，给出修改文件、测试输出、剩余风险和建议提交信息，等待成员C复核。

任何无法从仓库证据确认的事实都标记“待确认”，禁止猜测；任何正式效果结论只能使用胜/等效/负/未完成四档。
```

