# R3单策略合成验证指标

由`backend.evaluation.evaluate(events, config)`统一重算。输入包含scenario、evaluation_end_s、policy_id。事件须属于同run/policy、ID递增且时间不倒退，最后snapshot位于评价终点。

- 加权按时完整交付率：已到达且deadline<=终点的全部任务为分母，失败不删；完整任务最后一个有效块首次接收<=deadline才计收益。2:1两任务只成功前者为2/3。
- pending_task_count：已到达但deadline>终点的任务数，与是否已提前交付分开报告；未来未到达任务不计。
- success_payload_bytes：截至终点网关去重收到的有效载荷，包含未完整任务的部分块和迟到块；不含32byte头/16byte ACK。goodput_bps=该字节数*8/评价秒数。任务成功与字节成功是不同口径。
- joule_per_success_bit：全部星上背景/计算/发射/接收增量Wh*3600/去重有效bit；包含失败尝试与重传。无有效bit为null，reason=NO_DELIVERY。
- wait_p50/p95_s：有发送的任务首次发送时刻减arrival；线性插值百分位。未发送失败任务仍在业务成功率分母，不进入这个等待样本。
- minimum_soc_true：初值及各分段clip前事后snapshot的最小值。energy_violation_count是负值账本分段数，受快照分段影响，不冒称独立违例事件次数；精确持续时间尚未测量，为null+原因。
- 未定义关键任务集合/未运行学习策略时，相关指标为null+reason；真实测得0不附缺失原因。协议ACK_TIMEOUT事件不冒充求解器超时率。

R4规则运行有真实decision事件时，decision_p50/p95_ms由事件latency_ms线性插值重算；timeout_rate为MODEL_TIMEOUT决策次数/全部决策次数（MODEL_BUSY另由原因码追溯）。无decision的R3手工运行仍为null。规则回退也计入诊断样本；跨机器壁钟耗时不要求逐字节一致，重放使用保存的原事件。

这些是确定性manual_validation结果，尚不支持策略优越性、真实卫星或物理安全保证。对照实验前须扩展统一guard、基线、共享外部轨迹与最终全部指标。
