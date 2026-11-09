# A 黄金场景 AI 预期复核回执 · 2026-11-09

## 1. 裁定

状态：`accepted_with_notes`。

S1资源充足、S2低能量期限冲突、S3 ACK丢失重传的责任边界和预期语义可确认。B于2026-11-09交付的离线包包含唯一 `compile_sandbox_axes(axes, seed)` 构造器、S1/S2/S3真实sandbox run、健康对照和S3重复运行；A独立复算外层清单、事件语义与定向测试后，签收“黄金场景沙盒运行”。该签收不等于正式180条输入或540次策略运行完成，不证明Learned优于EDF/Value。

复核对象：

- B提交：`origin/codex/b-final-sprint-review-20261107@48157a8f4a1cdd7770685b79deb3fe4524b1bf7d`；
- A2语义：`docs/handoffs/A_interactive_ai_event_semantics_2026-11-09.md`；
- B机制实现：`training/policy_features.py`、`backend/policies/common.py`、`backend/policies/guard.py`、`backend/policies/runner.py`、`backend/simulator/protocol.py`、`backend/simulator/r3_engine.py`；
- 旧开发证据：`configs/scenarios/r3_*.json`、`docs/evidence/B/independent_2026-11-07/case_packet/`。
- B离线沙盒附件：`B_sandbox_offline_20261109.zip`，SHA256 `d637e638fcf1cf7baa4c178e3843afbd4847d85102df68ea2f6ef8d7ac08dc34`，`24,845,651` bytes。

旧 `r3_*` 手动场景及开发案例可以证明机制存在，但不能替代新版sandbox轴编译、配置哈希、run_id、事件和结果验收。

## 2. 统一责任边界

| 层 | 负责什么 | 不负责什么 |
|---|---|---|
| 冻结Learned评分器 | 根据公开Observation为任务×模式候选和idle评分 | 不保证最高分可执行，不控制ACK或重传 |
| Guard | 检查任务、单在途、窗口、时长、期限、功率、控制预算与能量储备，生成可执行动作 | 不学习价值函数，不预测未来真实信道 |
| 协议与重试控制器 | 发送、DATA接收、ACK、超时、同块重传和去重 | 不属于模型推理，不证明AI能力 |
| 事后评估 | 使用真实仿真事件计算结果和失败模式 | 不得把 `evaluation_truth` 回流给策略 |

健康档不是可直接显示成“AI动作”的开关。冻结评分器只读取 `energy_lower_Wh`、`soc_lower`、`capacity_lower_Wh`三个健康下界特征；Guard使用 `energy_lower_Wh`进行 `ENERGY_RESERVE` 检查。最终动作相同并不表示健康输入没有进入系统。

## 3. S1 资源充足

### 3.1 预期输入条件

- 初始能量10Wh；
- 无丢失或低丢失；
- 任务较少、期限较宽；
- health字段由B唯一构造器生成并满足 `energy_lower_Wh=soc_lower×capacity_lower_Wh`；
- 同一比较中的策略共享完整config、seed、窗口和随机流。

### 3.2 可观察变化

- 配置摘要和input/config hash反映资源充足条件；
- 任务候选的主要Guard检查通过，能量下界高于储备线；
- sent、received、acked链路完整，重传和fallback应相对少，但具体数量以真实事件为准；
- EDF、Value和Learned可能选择相同动作；
- Learned候选也可能并列，当前冻结模型曾出现robust/fast/idle同分并由确定性解码选择idle。

建议文案：

> 资源充足时多种策略可能给出一致动作。系统如实显示一致结果，不为突出AI制造差异。

### 3.3 不得承诺

- 不承诺Learned一定发送、一定最快或一定优于规则；
- 不承诺绝无fallback、丢包或超时；
- 不把策略一致写成“AI无效”，也不把成功发送全部归因于AI；
- 不用固定绿色动效代替真实事件状态。

## 4. S2 低能量期限冲突

### 4.1 预期输入条件

- 初始能量和健康能量下界接近储备边界，但两者的关系必须由B构造器明确，不得由C拼装；
- 高低权重任务竞争相同窗口；
- 期限存在冲突；
- 除待比较轴外保持seed、策略版本、模型SHA、代码和依赖锁一致。

### 4.2 可观察变化

- Observation中的 `energy_lower_Wh`、`soc_lower`或 `capacity_lower_Wh`与S1不同；
- candidate scores可能变化，因为三个健康下界进入冻结模型；
- `ENERGY_RESERVE`等Guard检查可能从通过变为拒绝；
- fast、robust、idle或fallback的分布可能变化；
- 能量曲线接近储备线，任务等待、期限和完成情况可能与S1不同；
- 若评分改变但最终动作一致，应同时展示“评分/约束变化”和“一致动作”。

建议文案：

> 保守健康下界同时进入候选评分和能量储备约束；高分发送候选仍可能因储备不足被拒绝。

### 4.3 不得承诺

- 不把 `ENERGY_RESERVE` 拒绝写成“AI识别危险”或“模型保证安全”；
- 不承诺低健康必然触发idle、robust或fallback；
- 不承诺Learned一定优先高权重任务，必须看实际分数和Guard结果；
- 不用健康/退化/临界前端标签补写RUL；`rul_est=null`必须保持null及reason code；
- 不用隐藏真实能量或未来最低SOC解释策略决策。

## 5. S3 ACK丢失与重传

### 5.1 预期输入条件

- ACK丢失概率或可见窗口安排能够真实触发ACK缺失；
- 至少一个任务包含多个数据块；
- 随机流和seed登记完整；
- Learned、EDF或Value只负责最初候选排序，协议负责闭环。

### 5.2 可观察变化

允许出现的真实事件链包括：

```text
sent
→ received(DATA)
→ dropped(ACK_LOST_WINDOW_CLOSED 或登记的ACK丢失原因)
→ fallback(ACK_TIMEOUT)
→ sent(同一task_id与block_id)
→ received(DUPLICATE_BLOCK)
→ acked
```

runner可根据公开协议事件产生 `RETRY_REQUIRED`，强制重传尚未确认的块。此时decision仍保留模型原候选分数，但最终重传动作包含重试原因。前端必须把“模型原评分”和“协议重试覆盖”分开显示。

建议文案：

> AI完成候选价值排序后，可靠传输仍由协议闭环负责；ACK缺失会触发同块重传和地面去重。

### 5.3 不得承诺

- 不写“AI检测ACK丢失”“AI执行重传”或“Learned解决协议可靠性”；
- 不把ACK未到写成任务已经完成；
- 不因收到重复DATA而重复累计有效载荷；
- 不保证每个seed都出现完整重传链；若该run未触发，必须显示实际事件而不是插入预制动画；
- 旧 `development_B_manual_ack_loss` 是开发期手动动作证据，不是新版S3策略运行。

## 6. 三场景对比的真实性门禁

每个场景至少交付：

1. 原始axes与B构造器版本；
2. 编译后的完整 `compiled_config.json`；
3. run_id、seed、config hash、input hash、model/policy/code SHA；
4. 完整事件分页或ZIP；
5. 至少两策略的后端results；
6. 事件摘要和一段不超过80字的说明；
7. sandbox/development来源标识；
8. 复现命令和结果。

三场景必须至少在输入哈希、事件序列或一个合法后端指标上形成可解释差异。若某两策略动作一致，应明确显示一致；不得通过前端颜色、随机数字或预制事件制造差异。

## 7. 本次运行复验

| 场景 | run_id | input / config hash | 事件与结果 | A裁定 |
|---|---|---|---|---|
| S1 | `sandbox_run_9809baca65f847d58fa961ccea9b635e` | `ba94d97c...` / `eec9e160...` | 103事件；EDF准时率1.0，Learned 0.0；两者能量违规均0 | 资源充足机制通过，保留Learned负结果 |
| S2 | `sandbox_run_245f69ffa2d54915a20b4574502dfd21` | `22b5eb46...` / `b4b6ff02...` | 96事件；两策略准时率均0；临界健康令发送候选能量检查失败 | 低能量/期限冲突机制通过 |
| S3 | `sandbox_run_5bc5191b2e5048fab07986e850b6edae` | `07363f4e...` / `79910cd8...` | 135事件；4次ACK丢失、5次超时、3次重复块、1次DATA丢失 | 协议闭环通过，不能归因于AI |
| S2健康对照 | `sandbox_run_1131f427c8f447ebadfcfdccb122b3eb` | `a7601619...` / `2579088c...` | 除健康轴外与S2一致；评分与Guard变化，Learned仍idle | A2机器门禁通过 |
| S3重复 | `sandbox_run_1f181a8e845c4405b16f3ee1897979fb` | 与S3一致 | 排除run_id与实测决策延迟后事件语义一致 | 确定性复验通过 |

S3可追踪到同一 `task_id/block_id` 的发送、ACK丢失、`ACK_TIMEOUT`、同块重传和 `DUPLICATE_BLOCK`；重复块没有被重复计入有效载荷。该链条属于协议与重试控制器，不属于Learned能力。

A还完成以下独立检查：

1. 外层 `SHA256SUMS.json` 的51个文件全部复算一致；
2. S1/S2/S3的axes、编译配置、run结果、事件和导出ZIP均存在；
3. `compile_sandbox_axes` 确实生成完整 `RunConfig`，并校验非法轴、seed、reserve和额外字段；
4. 在离线源码上运行沙盒、Learned API、Learned集成、策略runner与协议测试，结果 `54 passed, 1 warning`；
5. 包内旧 `offline_package.json` 记录的旧SHA/字节数与当前附件不同，列为归档来源备注；当前附件本体与外层交接单一致。

## 8. 当前证据能证明与不能证明的内容

可以证明：

- 新版S1/S2/S3由统一沙盒轴构造器生成，并具有受核run_id、输入/config哈希、事件和结果包；
- 不同HealthEstimate真实进入Learned评分和Guard；
- S3自动策略运行真实触发ACK丢失、超时、同块重传与去重；
- 冻结模型真实参与评分，但在本批S1/S2/S3中均选择idle或无交付；
- Guard和协议边界在该合成沙盒范围内成立。

仍不能证明：

- Learned优于EDF或Value；本批恰好提供了反例和负结果；
- 180条正式候选输入已经生成或三方签核；
- 540次正式运行已经执行；
- 该机器上的沙盒结果等同于换机复现或正式实验；
- Hybrid等新策略已经冻结、接入或通过预登记评估。

## 9. 交接状态

- S1预期语义：`accepted_with_notes`；
- S2预期语义：`accepted_with_notes`；
- S3预期语义：`accepted_with_notes`；
- 黄金场景沙盒运行验收：`accepted_with_notes`；
- 综合状态：`accepted_with_notes`；
- B下一步：保留本批负结果，等待C原始生成前回执后再进入180条候选生成与三方签核；
- C可做：使用本批真实沙盒事件呈现场景说明、责任边界、一致动作与负结果；
- C仍不可做：将沙盒运行写成正式效果结果，或将协议重传写成AI能力。
