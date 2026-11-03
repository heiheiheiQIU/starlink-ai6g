# B → A：reserve 与教师小批扩样支持域确认

日期：2026-11-04。状态：**B确认现有实现支持域，可据此开展新版本小批生成与审计**；新数据验收和模型训练另做。对应A请求：657f39c。

## 1. reserve 的准确语义

当前configs/policy.json和configs/teacher.json均使用0.5 Wh，配置及其SHA保持原样。plan_candidate在合法窗口、期限、功率和控制预算检查之后执行：

```text
air = 当前完整块(有效载荷+32 B头)的预测发送时间
ack_air = 128 bit / control_bps
horizon = max(decision_dt_s, air + data_propagation_s + slot_s)
cost_Wh = ((base_W+compute_W)*horizon + tx_W*air + ack_rx_W*ack_air)/3600
允许发送：energy_lower_Wh - cost_Wh >= reserve_Wh
```

不预支未来日照收益；deadline以预测数据接收时刻检查。Guard的预算与环境实际账本不是同一个对象；预测可行不构成真实SOC/储备线保证。idle仍有背景耗电，低于reserve时允许idle并不意味着能量被物理锁定在0.5。

本轮示例：robust=8192 bit/s、块1024 B、头32 B、decision_dt=2 s、slot=1 s、base=36 W、tx=36 W、ACK=8 W和1024 bit/s，得到air=1.03125 s、cost≈0.0309027778 Wh，数学启动门槛≈0.5309027778 Wh。0.49、0.5、0.51 Wh均拒绝该发送。接近门槛时fast可能比robust可行，不能给整个任务统一贴“不可行”而忽略模式差异。

当前浮点直接比较：在恰用浮点reserve+cost构造的门槛处，减法得到0.49999999999999994，robust仍被拒绝。A采样使用明确的±1e-6 Wh区分两侧，并原样调用教师，不擅加容差或改标签。原样保留等号点作为数值边界记录；数学等号与浮点实测分别披露。

审计中energy_lower<=0.5仅是“显式低能量覆盖”的一个谓词，遗漏了能量略高但仍不足以支付发送成本的状态；新审计另记录各模式plan_candidate的检查结果。

## 2. 当前教师硬边界与首批允许范围

| 项目 | 已有实现硬边界 | 本轮确认的小批范围 |
|---|---|---|
| 公开任务数 | 最多12 | 每来源1—4；空队列单列管线边界 |
| 预测窗口数 | 最多3 | 0—3，含当前无窗口、后续有窗口与完全无窗口 |
| 期限跨度 | <=min(240 s,120×decision_dt_s) | 所有可见任务deadline-now在0—30 s内；未来到达任务不放入Observation |
| payload | 每任务<=122880 B | 1—4096 B；采样时remaining>0，payload-remaining须为1024整数倍 |
| inflight与协议历史 | inflight不支持；教师不能从Observation恢复未公开的重传义务和待处理控制事件 | 只采无在途块、无待重传义务且控制事件已处理的状态；带inflight的样本计入不支持清单 |
| 预测数据损失 | 任意非零robust/fast概率返回UNSUPPORTED_LOSS | 标注输入所有预测loss为0；非零损失压力测试另存、不混入标签 |
| 预测协议 | 使用固定TeacherConfig.policy重建环境 | 保持现有参数：decision_dt=2 s、slot=1 s、传播0、control=1024 bit/s、ACK=8 W、base=36 W、compute/solar=0、robust/fast功率36/72 W、max_power=150 W |
| 速率 | 正值且能构成合法Window | 首批固定8192/16384 bit/s；优先变化期限、窗口和队列，不同时改物理参数 |
| 容量和能量 | 合同有限性、上下界与容量一致 | capacity_est/lower=20 Wh；energy_lower取0.1、0.49、0.5、0.51、模式启动门槛±1e-6、0.6、1.2、10 Wh中的代表值；soc/能量字段严格一致 |
| 求解预算 | 每调用整数1—5000 ms；每候选最多200 ms、20000节点 | 首批每调用1000 ms，先记录试跑CPU/壁钟；不延长预算掩盖超时 |

物理参数与教师policy保持同一版本，不能只改场景发射功率或reserve而仍用旧教师配置标注。无窗口、低能量、期限早于窗口均可返回OPTIMAL但只有idle或零效用；这些是合法边界，不是教师缺失能力。

首批来源轨迹采用显式确定性合成环境：不启用随机channel、数据/ACK随机丢失为0，实际窗口与已知预测窗口一致；这仅用于受控小批生成。教师仍只接收公开Observation，不读取环境真值。实际/预测失配、随机ACK丢失和重传留作独立域外压力测试，不混称已支持训练域。

特别注意：即使没有随机丢失，断窗仍可能导致ACK失败；超时后inflight可能已清空但retry_required义务仍存在。采样器须依据来源事件/协议记录确认 `inflight is None`、`retry_required_key is None`，且pending控制事件已清空，再导出公开Observation。该准入检查属于来源审计，禁止把私有协议对象或隐藏未来传给score_actions/solve_teacher。单凭教师返回OPTIMAL不能证明来源状态没有这些未建模历史。

UNSUPPORTED_TASK_COUNT/WINDOW_COUNT/HORIZON/PAYLOAD_RANGE/BLOCK_STATE/INFLIGHT/LOSS/FORECAST_CONFIG均保留状态与原因，不作为可学习的最优标签。TIME_LIMIT_FEASIBLE、NODE_LIMIT_FEASIBLE是受限可行解，不能改称OPTIMAL或gap=0。正式训练默认仅接收通过完整标签合同的OPTIMAL/gap=0样本；其他状态留作诊断。

任务仍可能在公共合同合法后被预测场景构造拒绝；上表是生成范围而非保证每条均可标注。完整valid/unsupported/timeout数量均须返回。

## 3. 给 A 的具体下一交付

1. 新目录建议data/teacher/a_n4_pilot_v1，使用新dataset_version与单独训练配置，不覆盖旧samples/splits/model/policy_train.json。现有生成器含固定版本常量，旧数据加载器与冻结审计CLI也强制20条、12/4/4及全部OPTIMAL，不能直接用它们验证新试点。A负责为新版本增加独立生成/校验/审计入口（建议training/audit_policy_pilot.py），按新manifest核对来源、实际分组数量与内容身份，保留旧冻结入口和测试；可以复用audit_rows统计函数，不能放宽旧入口约束来兼容新数据。
2. 先设计30条独立来源轨迹。建议24条来自有决策差异机会的期限/权重/任务冲突、短窗口等组合；其余6条覆盖低能量、无窗口、窗口前到期各2条。此比例是生成设计，不保证最优动作分布；实际标签如实报告。
3. 先按来源分组冻结train/validation/test，再由真实环境演进采每轨迹2—4个公开状态；不更换run_id复制旧初态，不读取隐藏未来。确保决策时的energy_lower已合法传播且available_at<=now。
4. 最多先生成60—120条有效状态；累计达到2 CPU小时或多次出现TIME/NODE限制时先交预算与覆盖报告，扩到原8 CPU小时总预算前由B根据实测评估。数量不足不放宽支持域凑数。
5. 交付来源清单/轨迹与时间/完整Observation/教师配置SHA/标签/支持状态/划分、内容去重与标签审计。先统计全部尝试的求解状态和排除理由，再对通过完整标签合同的可训练样本做审计，数量动态来自新manifest；unsupported/受限可行解另存诊断，不伪造成训练样本。额外区分“所有任务动作不可行”和“任务动作可行但效用为0”，给出每模式拒绝原因。
6. 保留所有idle和并列最优记录，不以提高非idle比例为目标删除困难样本或改教师；若辨识度仍弱，先解释任务期限与续行动作价值，再决定新的场景设计。B复验前不将小批数据称为正式训练集或启动新候选训练。

这份支持域确认使A可以开始小批生成与审计；不要求等待B完成WP2。旧冻结模型仍可用于B的接入与故障回归。非零损失和重传运行的learned泛化仍未验证，后续作为域外压力测试或显式回退单列。
