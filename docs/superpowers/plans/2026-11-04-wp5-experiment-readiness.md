# WP5 正式实验准备 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在等待A新模型期间准备可追溯的180轨迹输入、三策略运行和配对统计，11/06 20:00模型落位后形成正式冻结包。

**Architecture:** 保留现有R5开发验证入口和结果，新增独立formal_v1路径。先固化模型无关输入，再由已验收模型补全最终manifest；Runner、Guard、评价器继续共用。

**Tech Stack:** 现有Python、NumPy、pytest，JSON/CSV；不新增优化器或依赖。

**Spec:** `docs/handoffs/B_WP5_readiness_2026-11-04.md`；承接 `2026-11-02-project-optimization.md` 的WP5。此文为准备方案，以下新文件尚未实现，不是冻结回执。

## Global Constraints

- 18工况×10独立轨迹；edf/value/learned共540个唯一策略运行，每HTTP请求最多2策略不变。
- 公共Observation、Guard、协议及指标合同不变；模型无法绕过重传义务。
- 旧R5开发集与20样本冻结包不覆盖；新formal种子拟200000–200179，须经A来源/内容复核后才冻结。
- 未验新包时使用旧可信包；不自动登记任意manifest或HTTP模型路径。
- 非零损失属于教师训练域外，正式压力测试按域外单列，不能与训练域内混称泛化。
- 独立轨迹是统计单位，禁止把时刻、事件、重复EDF或训练种子当独立样本。

## Review Focus

- 输入文件或配置被改：重验SHA后拒绝启动，不能悄悄再生成。
- A训练来源和formal来源碰撞：拒绝冻结，保留冲突明细。
- 某策略失败或中途崩溃：保留原始状态，不删除轨迹、不以EDF结果冒充learned。
- 全零交付或null指标：分开N/A及真实0，不以跳过改变分母。
- 模型超时或过期回复：沿用WP2有界回退，并把成功模型决策/回退率写入统计。

### Task 1：冻结模型无关输入（第一项）

**Files:** 新增 `experiments/formal_v1/protocol.json`、`backend/formal_inputs.py`、`tests/test_formal_inputs.py`；生成配置存新运行目录，manifest记录每文件SHA；保留旧 `experiments/test_matrix.json` 不覆盖。

**Interfaces:** `materialize_inputs(protocol_path: Path, output: Path) -> dict`。输出180条trajectory_id/cell_id/seed/config_sha256/input_hash及生成器SHA；模型段状态pending不算最终冻结。

- [ ] 写失败测试：18×10唯一身份；新种子与旧10000–10179不交集；缺工况、重复seed、被改配置拒绝；同输入物化确定性；模型pending不可启动正式运行。
- [ ] 运行 `.venv\Scripts\python.exe -m pytest tests/test_formal_inputs.py -q`，确认测试因尚无实现失败。
- [ ] 在protocol中明确数值负载/能量/链路参数、任务/能源/信道生成算法、评价终点、健康准确反例、域内/域外标签。可复用 `backend.experiments.build_config`，但其2/6/10任务和0.8/1.2/10Wh是开发假设，不能仅改名视为已签核负载档。先按通信容量解释或调整定义，禁止看最终收益后挑参数。
- [ ] 实现物化函数；输入内容去重并与A数据来源核对，记录合法重复与拒绝理由。将输入包及协议交A/C复核。
- [ ] 同命令通过，核对180条哈希；提交 `feat(B): materialize independent formal experiment inputs`。

### Task 2：模型验包和最终冻结

**Files:** 新增 `docs/acceptance/A_N4b_B_2026-11-05.md`（实际日期据交付更新）；必要时新增独立运行配置、修改 `backend/api/inference.py`受信版本注册表、补 `tests/test_learned_api.py` 和 `tests/test_inference_lifecycle.py`。A目录文件仅由A交付。

**Interfaces:** 沿用 `inspect_model(config=None) -> dict` 和 `InferenceSupervisor(model_config=...)`；最终manifest必须含五文件SHA、模型配置SHA、数据版本和代码revision。

- [ ] 收到A交付后独立复算完整尝试/eligible数、状态分母、去重、group划分、训练归一化和9项审计；旧包SHA保持一致。未收到时登记blocked_by_delivery，不编造通过回执。
- [ ] 为新可信版本和未知/损坏manifest写用例，先验证未注册版本被拒绝，再以独立版本登记；不放宽旧包约束。
- [ ] 验新包正常评分、候选完整性、超时/崩溃/协议重传、ZIP身份；执行全库和真实HTTP。数据先验，新模型再验；未通过不投入正式运行。
- [ ] 11/05 22:00检查是否启用旧包后备；11/06 20:00将已验模型身份补入manifest，并由接收人复核后冻结；提交固定SHA。纯“换上新SHA”不构成验包。

### Task 3：三策略开发计时与正式运行入口

**Files:** 新增 `backend/formal_experiments.py`、`tests/test_formal_experiments.py`；读取Task1/2的manifest；不将旧R5入口变成正式结果。

**Interfaces:** `run_formal(manifest_path: Path, output: Path) -> dict`；只接收完整冻结manifest。输出逐策略run目录、append-only运行台账及状态，不覆盖任何已有run。

- [ ] 写失败测试：pending模型、改哈希拒绝；三策略同input_hash；失败仍留行；重复trajectory/policy拒绝；续跑只补缺失项且验证历史SHA；EDF与learned回退结果分别标识。
- [ ] 开发预设跑三策略，分别记录进程冷加载、暖评分p50/p95、端到端决策、整run耗时和fallback占比；正式540次预估包含启动/导出成本。任何开发探测目录都不得写formal结果标记。
- [ ] 实现正式入口，通过定向用例后完整回归。先运行冻结包的清单/哈希预检；三方冻结完成后才执行540次，明确失败/中断重试规则，全部尝试保留。
- [ ] 提交 `feat(B): execute traceable paired formal runs`；接收人签收前状态ready_for_review。

### Task 4：配对统计与四档裁决

**Files:** 新增 `experiments/analyze_formal.py`、`tests/test_formal_analysis.py`；输出summary.json、paired_deltas.csv、failure_ledger.csv；A复核统计定义，C消费签核claims。

**Interfaces:** `analyze_runs(manifest_path: Path, run_index: Path, output: Path) -> dict`；一条轨迹每策略最多一份预登记有效结果。

- [ ] **在正式结果产生前**登记：主指标为加权按时交付率；18工况等权；按工况内轨迹重采样的paired bootstrap（建议10000次，独立统计seed=20261104）；对两规则比较的多重性方法及等效界限须由A/B复核后写协议。
- [ ] 四档口径不能用“无显著差异”直接写等效。建议绝对差±0.02为待审等效界，置信区间完全落入才可等效；横跨界限保留未定/证据不足。模型/运行未完成列未完成。该数值当前仅提案，不能结果出来后再选。
- [ ] 写用例：已知相同/正差/负差、乱序同结果、重复样本拒绝、失败/null/零交付不静默丢失、工况等权、固定seed可复算。全失败批次不能生成“获胜”结论。
- [ ] 实现并跑定向测试，与A对小型手算样例交叉复核；11/07 20:00前输出总体/分工况差值、区间、回退、失败清单、域外适用性和材料口径，引用完整run与SHA。
- [ ] 提交 `feat(B): analyze paired formal outcomes with explicit limits`，交A/C复核；不把54条尚未实现的强优化器或不存在的RUL消融补成结果。

## 本轮自查与下一动作

已核对图片和C附件、现有生成器/Runner/受信模型入口、任务板及实验草案。新增输入、运行、统计互相独立可验；没有实现功能或假冻结。下一动作是Task1，同时收A新交付并安排C页面错误路径复验。
