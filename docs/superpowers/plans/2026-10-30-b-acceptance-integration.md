# 成员 B：H01 主验、训练门禁、seed 修复与分阶段集成

> **For agentic workers:** 使用 superpowers:executing-plans 逐项实施，步骤以复跑证据和接收人回执收口。本文是后续工作安排，不是验收完成记录。

**Goal:** 优先解除 A 的健康输入与训练交接阻塞，收口 seed 审计问题，按验收范围推进 R2→R5 入 main。

**Architecture:** 使用已有冻结合同、教师、仿真和 API；在固定提交上独立验收 A 的交付，B 的修复留在 B 分支。每层 PR 的验收与集成分别记录，不整支合并 A/C 功能。

**Tech Stack:** 现有 Python 3.12、Pydantic、pytest、FastAPI、Git/GitHub；本安排不新增求解器或训练依赖。

**Spec:** 用户 2026-10-30 提供的“三人的下一动”；v3 研发包《09_三人项目实施方案_详细执行与交接手册》尤其 H01/H02/H05 与第 15 节；CONTRIBUTING.md；以下固定远端回执。

## 已核实的起点（2026-10-30，香港时间）

已执行 `git fetch origin --prune` 和当前分支 `git pull --ff-only`。当前 B 分支 `feature/shared-channel-r5@50f441a` 已是最新；main 为 `75f1c52`。A 更新至 `bebe860`，C 更新至 `a1375b1`。没有将 A/C 整支代码合入当前工作区。

| 项目 | 可审计事实 | 后续含义 |
|---|---|---|
| H01 | A 的 `docs/handoffs/H01_health_estimate.md` 已交；实现源 `744b406`、证据 `5871a64`；返回冻结 HealthEstimate | B 立即主验；旧 H01_2026-10-28.md 是 legacy 审计，不替代此次正式适配验收 |
| R3 | A：`81a3e56` 中 `docs/acceptance/R3_A_2026-10-30.md`；C：`origin/feature/frontend:docs/acceptance/B_R3_C_2026-10-29.md` 第 6/7 节；均接受 `cac4b90` 的相应范围 | 新回执已补齐，不能继续把“缺 A 新回执”作为阻塞；合并与回归仍未执行 |
| H03 | A 的 `docs/acceptance/H03_A_2026-10-30.md` 接受 `9304766` 的指标口径；C 的 B_N3_H02 回执为 accepted_with_notes | 保留 C 未完成实时 HTTP 独立复跑的限制；A 指标接受不等于端到端接受 |
| H02 / R4 | C 的 `docs/acceptance/B_N3_H02_C_2026-10-29.md` 为 accepted_with_notes | 当前远端未找到 A 的 H02 签收回执，R4 尚不能视为全部门禁满足 |
| R5 | C 的 `docs/acceptance/B_R5_C_2026-10-29.md` 接受 `50f441a`，附限制 | A 的 R5 公平性/场景拆分复核回执尚未找到；180 条轨迹只是合成规则验证 |
| A 样本与切分 | `origin/feature/ai` 未找到 split_manifest.json、dataset_manifest.json、feature_order.json 或 H02 回执 | 准备检查清单，交付到达后再主验；不能代 A 生成签收或提前允许训练 |
| PR 链 | #3 R2→main；#4 R3→R2；#5 R4→R3；#6 R5→R4；均 OPEN、Draft、MERGEABLE | MERGEABLE 仅表示 Git 可合并，不表示验收通过 |

A/C 任务板部分行仍保留过期状态；以具体回执的目标提交和限定范围为准。本轮只读取回执和代码，没有重新运行验收测试。

## Global Constraints

- 冻结合同 schema_version=1.0；不私改 backend/contracts.py、configs/schema.json 或其他成员接口。
- 不修改 legacy 原件；不以旧预测、fixture、合成规则数据冒充真实测量或 AI 实验。
- 回执绑定提交、复跑命令、实际结果和产物哈希；未复跑不能签 accepted。
- H01 当前为 synthetic SOC/容量估计，不能解释为 legacy 模型已恢复真实在线健康能力。
- 保持已有分支历史，不强推、不在 main 开发，不把 C 前端或 A 未验收训练代码捆入 B PR。
- 截止采用香港时间 UTC+08:00：10/31 上午为样本与切分验收窗口；11/02 22:00 为 A 训练交付截止。下述 B 用时仅是工作预算，不是新承诺。

## Review Focus

1. 未来可用记录不能进入健康估计；缺 RUL 必须 null+原因，不能用 raw_fraction 代 SOC。
2. 同 run_id/原始轨迹派生的多个状态不能跨训练、验证、校准和测试集合。
3. 教师 UNSUPPORTED/TIME_LIMIT/NODE_LIMIT 与全零标签必须留存统计，不能隐藏失败或删难例美化数据。
4. 无信道请求的非零 seed、随机信道 seed 冲突、子结果与 ZIP 的记录必须一致。
5. 回执只覆盖其目标版本；栈式 PR 合并后的 base、diff、历史证据字节与合同都需复核。

## 任务 1：H01 主验，优先开始（10/30，预算 1–2 小时）

**输入：** A 固定提交中的 `backend/health/estimator.py`、`configs/health_observation.json`、H01 handoff、三样例及 manifest。

**输出：** `docs/acceptance/H01_B_2026-10-30.md`；`docs/evidence/B/H01_review_2026-10-30/`；运行原件放 `runs/h01_review_2026-10-30/`。

- [ ] 在 A 固定提交的隔离检出中复验，记录完整 SHA；不把 A 分支直接合入 B 工作区。
- [ ] 使用 B 可用 Python 环境执行 handoff 的成功和错误命令；错误例预期受控拒绝、退出码 2，不当作测试故障。
- [ ] 校验成功输出为冻结 HealthEstimate，检查 missing-RUL 视图及 RUL_UNAVAILABLE；能量/容量为 Wh、SOC 为 0–1、时间为秒。
- [ ] 运行 `tests/test_health_estimator.py tests/test_health_contract_adapter.py tests/test_h01_evidence.py` 与合同测试；核对未来 available_at_s、错误观测、陈旧数据及 legacy 原始输出的隔离行为。
- [ ] 复算 config、history、call_input、artifact SHA256；独立检查返回内容，不只认可 manifest 自洽。
- [ ] B 写 accepted / accepted_with_notes / changes_requested，明确仅接受 synthetic 适配范围；有阻塞则给输入、实际输出、期望和定位，不代改 A 实现。

**完成标准：** 成功、缺失、错误三类证据可定位，独立复测与合同校验通过，回执存在。验收通过后才在接入任务中使用该适配器。

## 任务 2：修复 seed P2（10/30，预算 1–2 小时，可独立执行）

**文件：** `backend/cli.py`、`backend/policies/runner.py`、`backend/api/worker.py`、必要的 `backend/api/service.py`；测试 `tests/test_api.py`、`tests/test_run_export.py`、`tests/test_policy_runner.py`、`tests/test_channel.py`。

**接口决策：** 保持公共 RunRequest/RunResult 不变。内部 RunConfig 增加可选非负整数 seed；API 为子运行传入 request.seed 的独立配置副本。有效 seed 优先显式运行 seed，其次 channel.seed，均缺省才为 0；显式 seed 与信道 seed 不等时拒绝。API 内层已有 seed 与请求冲突也应拒绝，不静默覆盖。子 config/results/manifest 明确记录同一有效 seed，不为修日志而新建随机信道。

- [ ] 先写失败测试：无信道 request.seed=7 时，两策略的 config/results/manifest 及 ZIP 对应文件均为 7，原请求对象不被修改。
- [ ] 补边界测试：seed=0、负数/非整数拒绝；带信道同 seed 一致；冲突返回 422；直接 CLI 未提供 seed 的旧配置仍可运行。
- [ ] 最小实现透传；保持同轨迹两策略 input_hash 相同；无信道两不同 seed 的物理事件/指标不变（排除 run_id、壁钟等运行元数据）。seed 改变必须能在配置及 config_hash 中审计。
- [ ] 定向 RED→GREEN 后跑全库；Windows 进程/HTTP 测试在允许的环境执行。先创建 runs 父目录，测试期间不改源码或 HEAD。
- [ ] 固定源提交后生成全新 API 运行包，复算产物哈希；旧 180 轨迹及旧 H03 证据保持原字节，不回填新 seed。
- [ ] 输出 `docs/handoffs/B_seed_P2_2026-10-30.md` 与 `docs/evidence/B/seed_P2_2026-10-30/`，推送 B 修复分支供受影响范围复核。

**完成标准：** 顶层、子运行、导出一致；既有协议及信道抽样语义不变。本项基于当前 R5 开发，不把 R5 信道代码倒灌进 R4；R4 的历史确定性 seed 备注保留，修复随 R5 层交付。

## 任务 3：准备并执行 A 样本/切分验收（10/30 准备，10/31 上午主验）

**B 可立即产出：** `docs/handoffs/A_training_gate_B_checklist_2026-10-30.md`，将以下要求发在仓库交接文件中；不代替 A 写训练器或产出其验收票。

**A 上游：** H02 独立调用回执、20 小场景教师样本、dataset_card、dataset_manifest、按 run_id/场景来源划分的 split_manifest、特征顺序/缺失 mask 与归一化来源。采用 09 第 15.2 节规定字段；若 A 采用其他路径，应在 handoff 显式映射，不擅改其目录。

- [ ] 先固定 A 交付 SHA；检查 H02 的教师版本、预算、gap、solver_status 及独立生成一条标签的实际证据。
- [ ] 校验样本逐行包含 sample_id/scenario_id/observation/candidate_scores/solver_status/gap/elapsed_ms/teacher_version/forecast_version；完整候选含唯一 idle，合同校验通过。
- [ ] 按 09 的 20 场景、每场景最多 4 状态核对采样记录；B 已有 20 个初始状态预跑不能冒充这一扩样过程。不能采集的状态须记录原因。
- [ ] 核对仅 OPTIMAL 纳入当前批准训练范围；保留不支持、超时、节点上限、全零标签及剔除计数。当前教师不支持非零预测损失，训练适用范围明确限定，不能改标签伪装支持。
- [ ] 检查 observation/特征无未来任务、真实信道抽样或真实环境能量；mask 与可见/到达/候选身份一致；缺失 RUL 不作有效 0 值。
- [ ] 对 train/validation/calibration/test 做 run_id、scenario_id、原始轨迹来源映射交集检查；同轨迹派生状态不得跨集合。核对 normalization 只由训练集拟合，测试列表/seed 不用于调参、阈值或 checkpoint 选择。
- [ ] 按 manifest 复算源样本与配置哈希，独立重生成一个支持范围内标签；保存测试和审计结果。
- [ ] 产出 `docs/acceptance/A_samples_split_B_2026-10-31.md` 与 `docs/evidence/B/A_samples_split_2026-10-31/`。阻塞时逐项列出，绝不因赶截止而预签通过。

**完成标准：** B 有可复现的样本、特征/mask、防泄漏与切分结论。交付未到只标 awaiting_delivery；这是训练前门禁，不等同 A 模型已经验收。

## 任务 4：R2→R5 分层集成（10/30 起，按各层门禁推进）

**输出：** `docs/handoffs/B_R2_R5_integration_2026-10-30.md`，逐层记录 PR、head/base SHA、回执范围、检查命令、合并 SHA；`docs/task_board.csv` 只按已证实范围更新。

- [ ] 整理 A/C 新回执的固定提交链接或保留原字节副本，不改写签收人原文；注明回执内“仍缺另一方”的旧段落已被哪个新回执消除。
- [ ] PR #3：先核查 R2 范围、四项手算和相邻复核。A 的 R3 回执包含 R2 测试，应核对是否足以覆盖 R2 合并范围；覆盖不全才补对应复核，不能从 MERGEABLE 推断通过。
- [ ] PR #4：核对 B 交付及 A/C 对 cac4b90 的回执已对齐；在 #3 入 main 后核查/调整 #4 base 为 main，再跑该层回归并集成。
- [ ] PR #5：A 的 H02 回执到达后核查首版教师范围；保留 C 的 accepted_with_notes 和 HTTP 复跑限制、seed 历史备注。#4 入 main 后核查/调整 base 和增量范围，符合门禁才集成。
- [ ] PR #6：核对 C 对 50f441a 的回执及 A 的 R5 公平性/场景拆分复核，新增 seed 修复另需覆盖受影响范围；#5 入 main 后核查/调整 base，测试通过才集成。
- [ ] 每层检查 frozen contracts/schema 差异为零，PR 中没有无关 A/C 功能；不重写已交接历史。合并前后记录代码、实际回归结果与证据源版本的区别。
- [ ] 更新任务板时区分 accepted、accepted_with_notes、merged、awaiting_delivery；不能把 R3 对齐扩大成 R4/R5 全部通过。

**完成标准：** main 中每一层有对应可审计验收和回归，依赖顺序正确。R4/R5 等回执期间，继续任务 1/2/3 的独立部分，不空等。

## 本轮之后的顺序

1. 先完成上述 H01、seed、样本门禁与可合并层；成熟优化器不占用 10/31 上午训练验收窗口。
2. 再推进成熟优化器及其支持边界；不因名称变化宣称已完成强基线。
3. A 模型通过交付验收后接入 learned 与健康输入，配合 C 做端到端联调。
4. H05 冻结后执行正式 AI/优化器对照与统计；现有 180 轨迹规则验证仍单独标识。

## 本次交付边界

本次已完成远端更新、回执/代码核对和本计划；尚未执行 H01 主验、seed 修复、A 样本验收或 PR 合并。未发现这些已存在资料无法读取；缺少的是远端尚未发现的 A H02/R5 回执和样本/切分交付，不把“未交付”写成“已验收失败”。
