# B 真实开发案例素材包

三例均为开发期验证，不是正式实验结果。JSON 保留原事件 ID、时刻、原因码和初始任务字节；CSV 可用于时序图。public_snapshots 已移除后验仿真真值，不得把真值回填为 AI 输入。电池能量以快照中的 energy_est_Wh/energy_lower_Wh 为准；事件 energy_Wh 仅表示该事件能耗。

- manual_ack_loss：手动动作脚本的 DATA 接收、ACK 丢失、超时、同块重传、去重与 ACK。
- corrupt_npz：隔离坏包回调导致 MODEL_UNAVAILABLE、EDF 回退；不代表受信生产入口允许坏包启动。
- constraint_reject：人为高分探针被 ENERGY_RESERVE 拒绝；不声称学习模型自然产生该分数。

每例包含少于 80 字说明、run_id/policy_id/input_hash、事件范围、原始证据路径和 SHA。截图、图形和正式材料插入仍需按团队流程复核。
