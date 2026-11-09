# R5 共享信道与规则矩阵实际验证

源代码：5375e99（完整SHA见verification.json）。实际执行18工况×10轨迹，两条规则共360次运行。全部180对input_hash/seed一致，全部360份运行的源码和产物SHA已逐一校验。

| 指标 | EDF | 价值密度 |
|---|---:|---:|
| 轨迹数 | 180 | 180 |
| 平均加权按时完整交付率 | 0.4869152046783626 | 0.553192007797271 |
| 成功去重有效载荷总量（byte） | 835584 | 823296 |
| 裁剪前负能量账本分段数 | 0 | 0 |

以上仅描述已列出的合成假设、准确健康边界和规则策略，不是AI实验或成熟优化器对比，不保证现实卫星、安全储备线或所有参数下相同结论。零负能量段也不等于证明不会跌破reserve。未做显著性检验、置信区间或正式测试集验收。

- per_run.csv含全部360行，summary.json为全量汇总，未删困难或零收益轨迹。
- manifest.json记录源版本、源代码、原登记矩阵和180个生成配置的SHA；artifact_inventory.csv列出本地完整运行包内所有文件SHA与大小。
- samples固定选择cell_00_trace_00、cell_09_trace_00、cell_17_trace_09，覆盖低/接近容量/过载三个负载标签；选择依据是索引，不是收益，含六份完整运行及三份输入。
- 全部配置、事件、账本及日志留在本机runs/r5/registered_180；未把数千份原始运行文件全部重复提交Git。换机可按交接命令生成同一批科学结果，再对照源/输入/结果，新的run_id和壁钟耗时会不同。
- full.xml为303 passed，targeted.xml为20 passed。prior-reader-lock-failure.xml保留曾出现的1 failed/301 passed，随后补确定性失败测试并修复读取重试后完整通过。
- 独立审查未发现阻塞/重要问题，另外检查混合损失的事件能量与账本，误差不超过2.8e-17Wh；不替代接收方验收。

重跑：在仓库根目录执行 `python -m backend.experiments --matrix experiments/test_matrix.json --output runs/r5/new_batch`。使用项目.venv和新输出目录。参数来源及抽样定义见docs/handoffs/B_R5_channel_2026-10-29.md；原54条优化子集仍仅是名单，未冒充优化器结果。
