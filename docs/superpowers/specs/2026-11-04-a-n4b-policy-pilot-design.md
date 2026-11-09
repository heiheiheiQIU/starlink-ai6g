# A-N4b 教师策略小批试点设计

日期：2026-11-04  
角色：A  
状态：待用户复核

## 1. 目标与边界

在不修改旧 A-N3 冻结数据、教师实现、仿真接口和 B/C 公共合同的前提下，
生成并审计新的 A-N4b 合成教师数据试点：

1. 设计 30 条独立的确定性来源轨迹；
2. 在采样前冻结来源级 train/validation/test 划分；
3. 用真实仿真状态演进采集每轨迹 2—4 个公开 `Observation`；
4. 用冻结教师重新求解，并分开保存可训练标签和诊断结果；
5. 审计来源、划分、内容身份、标签辨识度和边界覆盖；
6. 向 B 交付可复验小批包，本阶段不训练或替换 learned 模型。

实现分支为 `codex/a-n4b-pilot`，基线固定为
`f3c6938004283140bdaf5968f71df6d8be44483e`。不依赖仍为
`changes_requested` 的 PR #13，也不修改 `backend/contracts.py`、
`backend/policies/teacher.py`、`backend/simulator/`、`backend/api/`、
旧数据目录或旧训练配置。

## 2. 方案

采用独立试点管线，不泛化旧 A-N3 冻结入口，也不使用一次性脚本。这样既可复用
现有规范化、哈希和审计函数，又不会放宽旧 20 条数据的固定数量、全部 OPTIMAL
和 12/4/4 约束。

新增组件：

- `training/pilot_scenarios.py`：定义 30 条来源轨迹、确定性 seed、场景配置和
  来源级划分，不调用教师；
- `training/generate_policy_pilot.py`：通过
  `create_state → observe → step` 采样，检查来源协议状态，再将公开
  Observation 交给 `solve_teacher`；
- `training/audit_policy_pilot.py`：复算文件哈希、内容身份、split 继承、
  标签准入、覆盖和辨识度；
- `configs/policy_pilot.json`：固定版本、预算、数量、教师 SHA、划分和
  `training_enabled=false`；
- 三个对应定向测试文件，严格测试先行。

## 3. 来源、划分与状态采样

30 条来源包括：

- 24 条决策轨迹：1—4 个任务，组合期限冲突、权重差异、短窗口和 1—3 个窗口；
- 2 条低能量轨迹；
- 2 条无窗口轨迹；
- 2 条窗口前到期轨迹。

在状态采样和教师求解前，按来源 ID 的稳定 SHA256 排序冻结 18/6/6 的
train/validation/test 划分，保持 60%/20%/20% 比例。同一来源的全部状态必须继承
同一 split，禁止根据标签重新移动来源。

固定支持域：

- payload 为 1—4096 B，且 `payload_bytes - remaining_bytes` 是 1024 的整数倍；
- 可见任务期限在当前时刻后 0—30 s，未来任务到达前不进入 Observation；
- actual/forecast 窗口一致，robust=8192 bit/s、fast=16384 bit/s；
- 数据和 ACK loss 均为 0；
- capacity estimate/lower 均为 20 Wh，能量与 SOC 字段一致；
- 协议、功率和 reserve 与 `configs/teacher.json` 一致；
- seed 命名空间不得与旧 A-N3 或 PR #13 的 200000—200179 重叠。

每条轨迹采 2—4 个状态，总目标 60—120 个有效状态。idle 演进覆盖边界场景；
明确脚本动作只用于形成合法部分交付状态。动作必须由现有仿真器执行，且采样前满足：

- `state.inflight is None`；
- `state.protocol_state.retry_required_key is None`；
- `state.protocol_state.pending` 为空；
- 健康估计已经可用，任务已经到达。

私有状态仅用于准入检查，不进入教师输入、样本或特征。

## 4. 标签与产物合同

每个准入 Observation 使用 `budget_ms=1000` 调用冻结教师。

- 只有 `OPTIMAL + gap=0` 进入 `samples.jsonl`；
- `TIME_LIMIT_FEASIBLE`、`NODE_LIMIT_FEASIBLE`、`UNSUPPORTED_*` 和异常进入
  `diagnostics.jsonl`；
- `attempts.jsonl` 保存所有尝试，summary 保存状态和排除原因计数。

目标目录 `data/teacher/a_n4_pilot_v1/` 包含：

- `sources.jsonl`、`source_splits.json`；
- `attempts.jsonl`、`samples.jsonl`、`diagnostics.jsonl`；
- `summary.json`、`manifest.json`。

生成采用临时目录与原子发布，拒绝覆盖非空目录。manifest 记录来源、代码、教师配置
和全部产物 SHA256。旧 A-N4 中 `19/20` 是 idle 位于最优集合，真正的并列最优为
`6/20`；新审计必须分别报告两项。

## 5. 停止、失败与审计

- 累计教师 CPU 时间到 2 小时即停止，不自动扩到 8 小时；
- 多次出现 TIME/NODE 限制时停止并报告；
- 数量不足时不得放宽 loss、协议状态、公开信息或标签合同；
- 运行期间来源、代码或教师配置 SHA 变化时阻断发布；
- 重复来源、重复 Observation、跨 split、隐藏字段或未来信息使批次 blocked；
- 非零 loss、inflight、retry/pending、未来任务和不一致健康字段必须被拒绝。

审计区分：全部任务动作不可行、动作可行但效用为 0、idle 位于最优集合、并列最优、
唯一非 idle 最优，并如实报告三类边界来源的最终标签分布。

## 6. 验收

测试至少证明：

1. 两次生成的 30 条来源和 split 字节一致；
2. 来源 ID、seed、内容 SHA 唯一且与旧数据和 PR #13 不相交；
3. 18/6/6 划分完整互斥，所有状态继承来源 split；
4. 存在真实 `step()` 后的状态，不是复制初态改 run_id；
5. 教师只接收公开 Observation；
6. 三类边界各有 2 条来源；
7. 非完整标签合同的记录不会进入 `samples.jsonl`；
8. `training_enabled` 始终为 false；
9. 新定向测试和全库回归通过。

B 签收前，本试点不得称为正式训练集，不得启动模型训练，也不得宣称 learned
获胜、泛化成立或正式实验完成。

## 7. 非目标

- 不训练三种子模型，不生成新权重或 model card；
- 不修改 learned 五接口、guard、教师、仿真器或 API；
- 不运行 900 次正式实验；
- 不修复或合并 PR #13；
- 不删除 idle、并列最优或困难样本来改善指标；
- 不修改 legacy 原件。
