# A 黄金场景 AI 预期复核回执 · 2026-11-09

## 1. 裁定

状态：`changes_requested`。

S1资源充足、S2低能量期限冲突、S3 ACK丢失重传的责任边界和预期语义可确认；B现有代码也分别具备评分、Guard、协议与重试机制证据。但复核提交中尚无 `compile_sandbox_axes(axes, seed)` 或等价唯一构造器，也没有按新版S1/S2/S3协议交付的真实sandbox run包，因此A只签“场景预期语义”，不签“黄金场景运行验收”。

复核对象：

- B提交：`origin/codex/b-final-sprint-review-20261107@48157a8f4a1cdd7770685b79deb3fe4524b1bf7d`；
- A2语义：`docs/handoffs/A_interactive_ai_event_semantics_2026-11-09.md`；
- B机制实现：`training/policy_features.py`、`backend/policies/common.py`、`backend/policies/guard.py`、`backend/policies/runner.py`、`backend/simulator/protocol.py`、`backend/simulator/r3_engine.py`；
- 旧开发证据：`configs/scenarios/r3_*.json`、`docs/evidence/B/independent_2026-11-07/case_packet/`。

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

## 7. 当前证据能证明与不能证明的内容

当前可证明：

- 低健康能量下界能触发规则运行中的低能量行为；
- Guard实现了 `ENERGY_RESERVE`；
- 协议实现了ACK丢失、超时、同块重传和去重；
- runner可在公开ACK超时事件后维持重传义务；
- 冻结模型能输出完整候选集，Guard保持最终权威。

当前不能证明：

- 新版S1/S2/S3已由统一sandbox轴构造器生成；
- 三个黄金场景已有受签run_id、哈希和结果包；
- S1与S2不同HealthEstimate已通过真实Learned sandbox运行；
- S3在新版自动策略场景中已按规定触发；
- 任何场景证明Learned优于EDF或Value。

## 8. B补证与A复验步骤

B交付三场景包后，A按以下顺序复核：

1. 对照axes、compiled config和构造器版本；
2. 核对S1/S2的HealthEstimate差异及内部一致性；
3. 核对差异进入评分或Guard，而不是只改变前端标签；
4. 核对S3事件的task_id、block_id、ACK原因、重传与去重；
5. 确认协议行为没有被写成模型能力；
6. 确认RUL null、公开Observation和事后真值边界；
7. 核对两策略指标来自后端results；
8. 输出 `accepted`、`accepted_with_notes`、`changes_requested` 或 `blocked`。

## 9. 交接状态

- S1预期语义：`accepted_with_notes`；
- S2预期语义：`accepted_with_notes`；
- S3预期语义：`accepted_with_notes`；
- 黄金场景运行验收：`changes_requested`；
- 综合状态：`changes_requested`；
- B下一步：交付唯一构造器及三场景真实run包；
- C可先做：场景说明、责任边界、真实事件映射和一致动作提示；
- C暂不可做：使用旧fixture或开发案例宣称新版黄金场景已通过。
