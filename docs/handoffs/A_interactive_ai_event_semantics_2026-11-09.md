# A 在线 AI 事件语义与验收回执 · 2026-11-09

## 1. 裁定

状态：`accepted_with_notes`。

AI事件的字段语义、冻结模型身份、评分—Guard—协议边界及三个开发期样例已有可追溯依据。B于2026-11-09交付的离线沙盒包又提供了S2临界健康与同配置健康对照：除健康轴外输入一致，公开 `HealthEstimate`、冻结评分和 `ENERGY_RESERVE` 检查均发生可核对变化，因此A2机器门禁通过。两条Learned最终动作仍为idle，本文只签“健康差异真实到达评分/Guard”，不签“Learned产生更优动作”，也不构成formal结果签收。

复核对象：

- B集成提交：`origin/codex/b-final-sprint-review-20261107@48157a8f4a1cdd7770685b79deb3fe4524b1bf7d`；
- 公共合同：`docs/contracts/README.md`；
- Learned实现：`backend/policies/learned.py`、`backend/api/inference.py`、`backend/policies/runner.py`；
- 约束解码：`backend/policies/guard.py`、`backend/policies/common.py`；
- 特征编码：`training/policy_features.py`；
- 开发期事件证据：`docs/evidence/B/independent_2026-11-07/`。
- B离线沙盒交付：`B_sandbox_offline_20261109.zip`，SHA256 `d637e638fcf1cf7baa4c178e3843afbd4847d85102df68ea2f6ef8d7ac08dc34`，`24,845,651` bytes；
- 离线源码标识：包外说明登记 `71c40b0842ac9547895874288a1633d1f4fdb5ac`，功能提交 `3bd22a30d864eb0bdd0a32b8efea426e1673b803`，并发清理修复 `3f09926e78478c0ec235117d70fa605406977078`。

边界：本文不训练A-N4b、不生成新权重、不替换冻结模型、不修改B/C接口。`claim-A1`和正式效果claims继续保持 `pending`。

## 2. 冻结模型是否真实加载

Learned运行的受信路径不是只显示一个“AI”标签，而是执行以下身份校验后加载冻结包：

1. `configs/learned_policy.json` 指定 `model_version=a-n3-mlp-v1`、特征版本、包目录、权重SHA和归一化SHA；
2. `backend/api/inference.py::inspect_model` 校验受信manifest SHA、manifest结构、四个登记制品及逐文件SHA；
3. `numpy.load(..., allow_pickle=False)` 加载权重，并校验数组名、shape、`float32`与有限值；
4. 独立推理进程加载成功后才接受评分请求；
5. 成功评分的decision事件由runner写入 `model_version=a-n3-mlp-v1`。

冻结身份：

| 对象 | 值 | 来源 |
|---|---|---|
| model version | `a-n3-mlp-v1` | 模型配置与受信manifest |
| feature schema | `policy-features-v1` | 模型配置与manifest |
| weights SHA256 / run model hash | `a5226264d3a60f7d858e4d410595668b44b8dbd4c9a8bfa05191c1fd80461e4a` | 模型配置与manifest |
| normalization SHA256 | `5c5fd7e843817a63ed6c486ed1c2a525243a724a6573b01681e0aa53811d2449` | 模型配置与manifest |
| trusted manifest SHA256 | `949370f65165437a95b5858b23103b6cac892913592d1a4b54a3d3d4d27445a8` | B推理入口白名单 |
| policy version | `learned-r4-v1` | B runner运行时写入 |
| model source revision | `ff0589bfa465585158f76818a422ce6def3efc15` | 模型manifest |

显示规则：

- `decision.data.model_version` 表示该次成功评分采用的模型版本；回退事件中可为 `null`。
- `decision.data.policy_version` 表示策略/runner版本，不是模型权重版本。
- 模型哈希来自run的受信model metadata、manifest或结果包；当前decision事件本身不携带模型哈希。C不得根据 `model_version` 猜出哈希，也不得把policy version当作model version。
- 只有同时具备受信模型身份、run证据和成功decision事件时，前端才可显示“冻结模型已参与本次评分”。

## 3. `candidate_scores`语义

当前完整评分集合由“每个可见任务的robust/fast候选 + 恰好一个idle候选”构成：

| 字段 | 语义 | 显示要求 |
|---|---|---|
| `task_id` | 非idle候选所对应的当前公开队列任务 | 必须与候选模式一起显示；不能只显示最高分数字 |
| `mode=robust` | 对指定任务采用稳健速率档的候选价值分 | 是候选，不代表已发送 |
| `mode=fast` | 对指定任务采用快速速率档的候选价值分 | 是候选，不代表可执行 |
| `mode=idle` | 本轮不发送；其 `task_id` 必须为 `null` | idle是合法候选，不是异常或缺失 |
| `score` | 冻结评分器对公开Observation编码后的相对候选分 | 不解释为成功概率、收益百分比或安全证明 |

结构掩码与Guard必须分开解释：

- 特征编码器把“已有在途块、任务已过期、剩余字节为0”等结构上不可用的任务候选置为mask；当前冻结配置将其评分写为 `-1.0`。
- 窗口、链路时长、期限、功率、控制预算和能量储备等可执行性由Guard检查。高分候选仍可能被Guard拒绝。
- Guard只在通过检查的动作与idle之间选择；最终 `action` 才是可执行动作。
- 分数相同时，当前确定性排序还考虑公开估算成本、期限和稳定键；实际开发证据中三候选同为1.0时选择idle是合法结果，不得改写成“模型失败”。
- `candidate_scores`是评分输入证据，`constraint_checks`是可行性证据，`action`是解码结果。C不得把三者合并成一句“AI直接控制发送”。

## 4. 模型异常、超时和输入异常的回退

### 4.1 受信API启动前拒绝

模型包缺失、损坏、哈希不一致或manifest不受信时，当前HTTP入口在创建Learned run前返回422：

```json
{
  "code": "INVALID_CONFIG",
  "message": "Frozen learned model package is unavailable",
  "details": {"reason": "MODEL_UNAVAILABLE"}
}
```

这种情况没有成功创建的Learned run，前端应显示“模型包验签失败/运行未创建”，不能显示EDF已替代本次正式Learned运行。

### 4.2 运行期受控回退

已创建运行中的评分异常由gateway转为受控规则回退：

| 原因码 | 当前含义 | 前端行为 |
|---|---|---|
| `MODEL_UNAVAILABLE` | 运行期评分进程、模型或回调不可用 | 标记fallback，显示规则动作及原因 |
| `MODEL_TIMEOUT` | 超过评分预算 | 标记fallback，不继续显示旧评分 |
| `MODEL_BUSY` | 旧的异步回调尚未结束 | 标记fallback，不复用迟到结果 |
| `INVALID_SCORE` | 候选缺失、重复、非有限或引用不可见任务 | 标记fallback，显示合同校验失败 |
| `NO_VALID_CANDIDATE` | 非空任务队列没有结构可用的发送候选 | 标记fallback，保留实际规则动作 |

回退路径使用EDF候选重新进入同一个Guard，不绕过窗口、功率、期限或能量约束。`fallback=true`与 `action.reason_codes`必须同时显示；不能只展示最终动作而隐藏AI异常。

当前实现没有独立的 `INPUT_OUT_OF_RANGE` decision原因码。非法HTTP配置应在创建时按422拒绝；进入评分器后的Observation/特征异常在当前gateway中可能折叠为 `MODEL_UNAVAILABLE`。C不得自行发明“输入越界”事件；若B要细分原因码，必须按H00合同变更流程交付。

## 5. 公开Observation与事后真值边界

评分器允许读取：

- 当前 `sim_time_s`、公开缓存字节数；
- 已到达任务的到达、期限、payload、剩余字节、权重和业务信息；
- 预测窗口中的速率和丢失概率，而非实际未来信道结果；
- 当前公开健康估计；
- 当前在途块及其公开协议状态。

冻结评分器实际使用的健康特征只有：

1. `energy_lower_Wh`；
2. `soc_lower`；
3. `capacity_lower_Wh`。

`rul_est`不是冻结评分器特征。当前native RUL不可用时必须保留：

```json
{
  "rul_est": null,
  "rul_unit": null,
  "reason_codes": ["RUL_UNAVAILABLE"]
}
```

禁止用前端“健康/退化/临界”标签反推或补写RUL。

评分器禁止读取：

- 未来真实丢包、ACK是否会成功、最终任务收益；
- 环境内部真实容量、真实SOC或未来最低SOC；
- 其他策略未来结果；
- `snapshot.data.evaluation_truth`。

`evaluation_truth`只允许用于事后评估，并必须保留 `label=posthoc_simulation`。事件顶层 `energy_Wh` 是该事件的增量耗能；电池剩余状态从snapshot的估计字段读取，不能由单个事件耗能代替。

## 6. 健康变化可能影响什么

健康变化通过三个保守下界特征进入冻结模型，也通过 `energy_lower_Wh` 进入Guard的 `ENERGY_RESERVE` 检查。因此它理论上可能改变：

- robust、fast、idle的相对评分；
- 高分发送候选是否因能量储备被拒绝；
- 最终动作与fallback/idle比例。

但不承诺每次健康档变化都会改变最终动作。模型可能在两个输入上给出相同排序，或者评分变化后仍被同一约束裁决。此时前端应如实显示“健康输入已变化，但本状态下最终动作一致”，不能制造颜色或数字差异。

## 7. 三个开发期事件片段

以下三例均不是formal结果，也不证明Learned优于规则。

### 7.1 正常评分：真实冻结模型事件

来源：`run_87a1856ace8e4c1c97642a5ea3b9be47`，Learned event 21，B提交 `48157a8f...`。

```json
{
  "event_id": 21,
  "policy_id": "learned",
  "event_type": "decision",
  "data": {
    "action": {"task_id": null, "mode": "idle", "scheduled_bytes": 0, "fallback": false},
    "candidate_scores": [
      {"task_id": "T1", "mode": "robust", "score": 1.0},
      {"task_id": "T1", "mode": "fast", "score": 1.0},
      {"task_id": null, "mode": "idle", "score": 1.0}
    ],
    "fallback": false,
    "model_version": "a-n3-mlp-v1",
    "policy_version": "learned-r4-v1"
  }
}
```

解释：模型成功加载并返回完整有限候选；三者并列，Guard确定性地选择idle。该例只证明正常评分链路成立，也再次体现冻结小样本模型的辨识度限制。

### 7.2 Guard拒绝高分候选：注入探针

来源：`development_B_20261107_constraint_reject`，event 3，`data_scope=development_only`。

```json
{
  "candidate_scores": [
    {"task_id": "T1", "mode": "robust", "score": 10.0},
    {"task_id": "T1", "mode": "fast", "score": 10.0},
    {"task_id": null, "mode": "idle", "score": 0.0}
  ],
  "constraint_checks": [
    {"code": "ENERGY_RESERVE", "passed": false, "details": {"task_id": "T1", "mode": "robust"}},
    {"code": "ENERGY_RESERVE", "passed": false, "details": {"task_id": "T1", "mode": "fast"}}
  ],
  "action": {"task_id": null, "mode": "idle", "reason_codes": ["ENERGY_RESERVE"]},
  "model_version": "injected-high-score-probe-not-trained-AI"
}
```

解释：这是人为高分探针，不是冻结模型自然输出。它只证明“高分不能越过能量储备约束”。截图和材料必须保留“注入探针/开发期”标识。

### 7.3 模型异常回退：隔离损坏包

来源：`development_B_20261107_corrupt_npz`，event 3，`data_scope=development_only`。

```json
{
  "reason_code": "MODEL_UNAVAILABLE",
  "data": {
    "action": {
      "task_id": "T1",
      "mode": "fast",
      "scheduled_bytes": 1024,
      "reason_codes": ["MODEL_UNAVAILABLE"],
      "fallback": true
    },
    "fallback": true,
    "model_version": null,
    "policy_version": "learned-r4-v1"
  }
}
```

解释：隔离故障注入使评分回调不可用，runner使用EDF候选并继续通过Guard。受信HTTP入口面对缺失/损坏冻结包会在run创建前返回422，因此此例不能被解释为“生产入口允许坏模型继续运行”。

## 8. A2机器验收复验结果

复验对象为离线包中的 `golden_runs/S2/` 与 `golden_runs/health_control/`。A独立解包、比对JSON及事件，结果如下：

| 项 | S2 临界健康 | 健康对照 | 裁定 |
|---|---|---|---|
| seed / policies | `7` / `edf,learned` | `7` / `edf,learned` | 一致 |
| 除健康轴外配置 | 任务、期限、权重、能量、储备、扰动、速率相同 | 同左 | 一致 |
| health axis | `critical` | `healthy` | 唯一主动变化 |
| `soc_est` | `0.04` | `0.04` | 相同 |
| `soc_lower` | `0.037142857142857144` | `0.0392` | 不同 |
| `capacity_lower_Wh` | `14.0` | `20.0` | 不同 |
| `energy_lower_Wh` | `0.52` | `0.784` | 不同 |
| `rul_est` / reason | `null` / `RUL_UNAVAILABLE` | `null` / `RUL_UNAVAILABLE` | null语义保持 |
| Learned评分 | 与对照不同 | 与S2不同 | 健康差异到达评分器 |
| Learned Guard | 四个发送候选均 `ENERGY_RESERVE=false` | 对应能量检查均为true | 健康差异到达Guard |
| 最终动作 | idle | idle | 真实一致，不挑选结果 |

此外：

1. `compile_sandbox_axes` 是唯一编译入口，健康下界满足 `energy_lower_Wh=soc_lower×capacity_lower_Wh`；
2. reserve上限、非法轴、非法seed、额外字段和目录逃逸均有校验或测试；
3. A在离线源码上独立运行 `test_sandbox.py`、`test_learned_api.py`、`test_learned_integration.py`、`test_policy_runner.py`、`test_protocol.py`，结果为 `54 passed, 1 warning`；
4. 外层 `SHA256SUMS.json` 登记的51个文件全部独立复算一致；
5. 离线包内部 `docs/evidence/B/sprint_2026-11-09/offline_package.json` 仍记录旧包 `36de40f1...` / `24,770,339` bytes / source `3f09926...`，与本次附件不一致；当前附件本体与外层交接说明一致，因此列为来源元数据备注，不推翻机器语义验收。B后续归档应删除或明确标注该旧收据，避免将其误作当前附件证明。

## 9. 给C的最小显示合同

1. 同时显示评分、Guard检查、最终动作和fallback原因；
2. 成功Learned评分显示model version，模型哈希从run证据区读取；
3. fallback时不保留上一轮AI评分制造“连续AI决策”假象；
4. injected probe、fault injection和sandbox均显示来源，不进入formal claim；
5. `rul_est=null`显示“不可用 + reason code”，不显示0；
6. 分数相同或动作一致时明确显示一致；
7. `evaluation_truth`只放事后评估层，绝不显示成模型输入。

## 10. 交接状态

- A语义复核：`accepted_with_notes`；
- A2机器验收：`accepted_with_notes`；
- 综合状态：`accepted_with_notes`；
- B下一步：归档时修正或隔离包内旧 `offline_package.json`，不得用旧收据证明当前附件；
- C可做：字段映射、来源标签、null/fallback/Guard显示，并使用S2/健康对照说明“评分与约束变化、最终动作仍一致”；
- C仍不可做：把该沙盒对照写成正式效果结果，或用前端预设等级补写RUL和模型哈希。
