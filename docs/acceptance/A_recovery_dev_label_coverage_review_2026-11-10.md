# A recovery 开发试点标签、覆盖与训练门禁裁定（2026-11-10）

`A_ruling=accepted_with_notes`；`machine_audit.status=passed`。

裁定对象是 B 开发试点快照 `a2e0be4b579b5d4cb797bdc826c077e551d985f6`，不是正式 540 结果。A 仅接受已审计范围内的标签/完整性一致性；覆盖不足，`training_enabled=false`、`training_approved=false`，训练门禁继续关闭。

## 1. 证据边界与事实表

唯一机器事实接口：[A_recovery_dev_audit.json](../evidence/A/recovery_dev_2026-11-10/A_recovery_dev_audit.json)。该接口 SHA256 为 `d99eaa2209007b2be1870eb3f7a188326d111c792e3134d3e34f1c8e253e744e`。下表转录 A 独立机器审计的重算/核对结果；本裁定未重新运行 B 的生成器或求解器。B 自报的 `1703` checks 只作为自报背景，不等于 A 独立重算的检查数量，不用于扩大验收范围。

来源门禁固定上述 B commit，并以冻结 manifest 的 SHA256 `01be0d640ffdde85f30856ea03e73f548575217a9eba513971c0cc7a579f7e90` 为可信锚。机器接口 `source_verification.status=verified` 表示完整代码清单及所消费试点输出与该冻结引用相符（允许等价 JSON 排版及哈希字母大小写）；不证明无关仓库文件的来源。错误 commit、删去代码清单条目或改写引用 manifest 均拒绝。候选诊断必须非空、无重复，与 `feasible=true` 评分候选身份集合精确一致，每项 `limited` 必须存在且为 null；不可行发送的评分仍保留作决策证据，不要求其拥有求解诊断。

| 项目 | A 审计结果 |
| --- | --- |
| source commit | a2e0be4b579b5d4cb797bdc826c077e551d985f6 |
| sources / states | 30 / 60 |
| source split: train / validation / test | 18 / 6 / 6 |
| state split: train / validation / test | 36 / 12 / 12 |
| prior_observation_count | 248 |
| audit status | passed |

family 分布按 source 计，总和 30；decision 分布按 state 计，总和 60。family 名称不是标签优势的证据，`must_wait` 或 `wait_then_send` 不代表存在 strictly-wait-better。

| family_counts | source count |
| --- | --- |
| `last_chance` | 8 |
| `must_wait` | 7 |
| `task_conflict` | 7 |
| `wait_then_send` | 8 |

| decision_counts | state count |
| --- | --- |
| `no_feasible_send` | 22 |
| `send_strictly_better` | 30 |
| `tied` | 8 |
| `wait_strictly_better` | 0 |

teacher/solver 结论只限于绑定与状态一致性：`teacher_binding`、`solver_status` 均 passed。审计明确为 consistency audit，teacher scores 未独立重求解。接口没有给出每种具体 solver status 的分项数量，本文不补造，也不将 passed 写成独立最优性或数值正确性证明。

| 独立审计检查 | 结果 |
| --- | --- |
| `exclusion_evidence_hashes` | passed |
| `label_content_hash` | passed |
| `manifest_hashes` | passed |
| `semantic_observation_leakage` | passed |
| `solver_status` | passed |
| `source_identity_split_uniqueness` | passed |
| `source_level_split` | passed |
| `state_identity` | passed |
| `summary_reconciliation` | passed |
| `teacher_binding` | passed |
| `unique_content_hash` | passed |
| `unique_seed` | passed |

泄漏裁定范围：仅认可接口中 source-level split、source identity/split uniqueness、unique seed/content hash，以及与 248 个 prior observations 的 semantic observation leakage 检查和 exclusion evidence hashes 核对。完整排除证据文件路径和哈希以接口 `file_sha256` 为准，包括其中列出的先前 teacher 数据及冻结正式候选配置。此范围不等于对未列入接口的数据、未来样本或所有统计依赖作无泄漏保证；同一 source 的两个 capture 必须视为同一来源，60 states 不可当作 60 个独立来源。

## 2. 文件身份

以下为接口登记的全部 10 个 `pilot/` 文件 SHA256；`pilot/` 是审计接口中的命名空间，不是本裁定另建的目录。其他 repo/zip 输入的完整哈希保留在唯一机器事实接口中，不把本表当作全部输入的替代清单。

| 文件（审计接口键） | SHA256 |
| --- | --- |
| `pilot/attempts.jsonl` | `994cf2504ab28a6f784d6b84fb51ebd069ad19e60a9e0ffd04dea128401e43e7` |
| `pilot/config.json` | `204af11c07bad04fb25e085c733b63415306d0eb48bfc14c6bed657b99ed9c8c` |
| `pilot/diagnostics.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `pilot/leakage.json` | `09049fa30729e613968f8c43f1e7b40582ff4d29d7b55b2c407b3629a9a20294` |
| `pilot/manifest.json` | `01be0d640ffdde85f30856ea03e73f548575217a9eba513971c0cc7a579f7e90` |
| `pilot/samples.jsonl` | `994cf2504ab28a6f784d6b84fb51ebd069ad19e60a9e0ffd04dea128401e43e7` |
| `pilot/source_splits.json` | `2b23a9b586183964c8d1d311edcf319f6a4efe36813a2594aa67bd32aad22714` |
| `pilot/sources.jsonl` | `332168dcdafdc9730030d499196e319c1c327dccdb637adf68970a5a30a9948e` |
| `pilot/summary.json` | `7e6b8d4628fd8869c56bd6ac31df2817d5a7afd7c45137c44fd31481dffe4549` |
| `pilot/teacher_config.json` | `c75eb37ba7bf55de2ed8efc9bdcf9c03fb17a866b2bccd2019e1cea590c72353` |

## 3. 覆盖缺口与门禁

| coverage_counts | covered states |
| --- | --- |
| `in_flight` | 0 |
| `long_horizon` | 0 |
| `non_zero_loss` | 0 |

- strictly-wait-better：`wait_strictly_better=0`；无可发送状态下只能等待的 22 个 `no_feasible_send` 不填补“可发送但等待严格更优”的缺口；8 个 tied 也不填补。
- non-zero packet loss / ACK loss：审计定义为任一 source 的 true/public forecast loss 或 ACK loss > 0，计数 0。不能由零损失试点推断抗丢包或 ACK 丢失表现。
- in-flight / retransmission：审计可测定义是 public observation inflight 非 null，计数 0。接口未单列 retransmission 计数，当前 in-flight 覆盖为零，也未提供重传覆盖证据；不得声称已覆盖重传。
- long-horizon：审计定义为剩余 public task/window horizon > teacher horizon_s（240 seconds），计数 0。当前两次 capture 的短轨迹不能证明跨越此边界的长期策略能力；增加同一短轨迹 capture 数也不自动填补此缺口。

以上任何一项为零，都必须保持训练门禁关闭；本次四项均缺失。不推断泛化，不把无优势、打平或不可发送状态改写为算法收益。

## 4. 最小补样合同（下一版要求，不是已完成事实）

1. **新版本和新目录**：另行登记版本 ID、独立数据目录、生成代码 commit、teacher/solver 配置、manifest 与 SHA256，禁止覆盖或原地追加现有 pilot。原 pilot、正式 540 结果及其配置/清单/归档须逐字节保留；生成前后比较冻结哈希。开发补样及其分析与正式结果单独存放、单独标识，不回填正式表格。
2. **新 seed 区间**：在生成前登记明确的起止值、用途和划分；依据冻结试点、先前 teacher 数据、正式结果及新 held-out 登记表检查不重叠。现接口未给出可用数值区间，因此本文不宣称某区间已空闲；未完成该登记与排除检查不得接收补样。seed 唯一之外还要核对 source 身份、内容哈希和语义 observation。
3. **source-level train/validation/test 隔离**：生成前冻结来源划分，任一 source 的全部 capture、派生样本、重传延续及同源变体都留在一个 split。不得先按 state 随机切分，也不得从 validation/test 选样再回流训练；逐项报告 source/state 数与交集为零的证据。
4. **每个缺口在 train、validation、test 各至少 1 个独立 source**：这是最小存在性验收下限，不是足以训练或推断泛化的规模论证。逐 split 交付覆盖矩阵和 source/state ID；可重叠满足多项的同一 source 不能重复算作独立来源。至少覆盖下表的每一行，不可用 family 名称代替实际状态和标签。

| 定向补样行 | 可复验的最低证据 |
| --- | --- |
| 可发送且等待严格更优 | 至少有一个 feasible send；冻结 teacher 目标、tie 容差与比较规则；独立核对 wait 分数严格优于所有可行 send；保留分数/求解状态 |
| packet loss | true/public forecast 中实际 packet loss > 0 的状态；记录概率、seed 和标签，不只改 family 名称 |
| ACK loss | ACK loss > 0 的状态；与 packet loss 分开列示，并保留 ACK 状态证据 |
| in-flight | public observation inflight 非 null 的捕获状态，附 source/capture 身份和标签 |
| retransmission | 实际重传/重传待决状态及协议事件证据，单独列示，不用 in-flight 非 null 自动替代 |
| long-horizon | 剩余 public task/window horizon > 240 seconds 且超出冻结 teacher horizon；记录连续轨迹与后续决策，说明 teacher 截断与求解有效性，不能只复制两次 capture |

5. **单独登记 held-out evaluation**：在任何拟训练前，独立登记 held-out 来源、seed、目录、冻结哈希、覆盖矩阵、策略比较项、指标及判定规则。它必须与 train/validation/test 和正式 540 来源分离，不能用于调参、筛选来源或挑选 checkpoint；首次登记不代表已经执行，也不代表收益成立。
6. **重新独立审计与 A 复审**：交付 attempts/samples、sources/splits、diagnostics、teacher 配置/绑定、状态和目标证据、manifest/hash、泄漏排除输入及分项检查结果。所有失败、不可行、tie 和求解未完成均如实列报；严禁伪造 wait 标签来凑数量。对严格优势及长期标签补交独立重求解/可核对证据。若 teacher 当前不能可靠标注目标缺口，须先单独评审 teacher 扩展，不能把未认证样本视为合格补样。

上述合同仅允许规划并提交下一版开发数据供审计。满足存在性下限仍须就样本规模、覆盖质量、标签有效性和 held-out 方案另行作 A 的训练批准，禁止自动开门。

## 5. 给 B/C 的批准与未批准范围

**批准**：可引用本快照 30 sources / 60 states 的标签/完整性一致性验收，必须同时披露零覆盖缺口、teacher 分数未独立重求解和训练未批准。可按最小合同准备新版本开发补样并提交复审。

**未批准**：`training_enabled=false`、`training_approved=false`；不训练，不启用 Hybrid，不替换 `a-n3-mlp-v1`，不修改正式 540 结果；不得宣称 AI 收益，不将该开发试点与正式评估合并。本文不编辑 B/C 文件，不改变现有模型、策略开关或正式结论。本次裁定保持训练门禁关闭；负结果仍按负结果披露。
