# B 授权代审与全量实验交接 · 2026-11-10

180 条登记输入、EDF/Value/原始 Learned 共 540 个唯一策略运行已完成，失败、缺失、中断及重试均为 0。执行源码为 48157a8f4a1cdd7770685b79deb3fe4524b1bf7d，统计使用已登记的 18 工况等权、每工况 10 条配对轨迹及 10000 次配对 bootstrap。统计裁定为负，结果发布签核 result_signoff 保持 pending。

## 审核身份和授权

用户授权“能不能替ac进行检查，直接推进下一步”。两个独立上下文的代理分别实际复核来源和库存，采用 codex-delegated-A-source-review 与 codex-delegated-C-inventory-review 身份签署回执，B 回执为 member-B。代理回执及授权随冻结包保存。来源检查 542 项通过，库存检查 25 项通过，随后既有 index、freeze、verify 工具全部通过。[授权记录](../evidence/B/delegated_execution_2026-11-10/authorization.json)

本批采用授权代理审核。团队人工 A/C 的最终签名及结果发布回执继续按实际状态登记。候选、模型、三策略集合和统计规则沿用原登记对象。

## 实测结果

| 策略 | 轨迹数 | 工况等权加权按时交付率 | 成功载荷总字节 | 能量违规 |
|---|---:|---:|---:|---:|
| EDF | 180 | 46.54% | 937984 | 0 |
| Value | 180 | 51.15% | 880640 | 0 |
| Learned | 180 | 0.00% | 0 | 0 |

| 配对比较 | 平均差，百分点 | 95% 区间，百分点 | 轨迹胜/平/负 |
|---|---:|---|---|
| Learned−EDF | −46.54 | [−49.42, −43.59] | 0/15/165 |
| Learned−Value | −51.15 | [−53.86, −48.31] | 0/11/169 |

区间采用登记的逐比较口径。结果适用域为 synthetic_out_of_zero_loss_training_domain。Learned 的 2160 次决策全部选择 idle，模型成功决策计数为 2160，推理回退为 0。本机端到端决策时延中位数为 3.062 ms，P95 为 5.755 ms。

两组比较各有 180 个完整配对，每工况均有 10 个样本。独立结果审查直接读取原始结果与台账，并复算 bootstrap，均值和区间逐项一致。[分析摘要及分工况结果](../evidence/B/delegated_execution_2026-11-10/analysis/summary.json) · [360 条配对差](../evidence/B/delegated_execution_2026-11-10/analysis/paired_deltas.csv) · [独立结果复算](../evidence/B/delegated_execution_2026-11-10/A_result_audit.json)

## 执行与证据

smoke 完成 3 个运行，cell 累计 30 个，coverage 累计 81 个，full 累计 540 个，所有阶段复用同一个台账。前两段实测后登记并发 1、容量和剩余耗时估计，全量前保留了运行前记录。四段墙钟累计约 219.8 秒，统计约 18.0 秒。[运行前容量记录](../evidence/B/delegated_execution_2026-11-10/pre_full_capacity.json) · [逐段命令和日志](../evidence/B/delegated_execution_2026-11-10/stage_logs/full.json)

每次运行保留输入哈希、模型身份、代码与源码 SHA、策略、seed、事件、结果、能量账本及日志。540 个唯一运行键对应 1080 条 started/completed 台账记录。[完整台账](../evidence/B/delegated_execution_2026-11-10/run_index.jsonl) · [540 行指标图源数据](../evidence/B/delegated_execution_2026-11-10/export/metrics_by_run.csv)

本批事件例包含真实 ACK 超时/重传及 Learned 等待。安全 Guard 拒绝与模型故障回退继续提供原有沙盒及受控注入案例，分别记录来源，统计样本量为本批 540 个运行。[本批事件例](../evidence/B/delegated_execution_2026-11-10/export/event_cases.json) · [历史工程补充例](../evidence/B/delegated_execution_2026-11-10/supplementary_engineering_cases/scope.json)

## 接收与复现

[完整结果包](../evidence/B/delegated_execution_2026-11-10/formal_v2_delegated_results_20261110.zip) 大小 13,617,292 bytes，SHA256 为 efa801d9dde6a9eb340ca0a27b873027248edbcadd7b85c82cdd3847ab5f9e86，共 4009 个成员。包内含原始冻结源码 source_48157a8.zip、冻结输入与模型、代理回执、全部运行原始文件、统计、图源数据、授权和逐段日志。PACKAGE_MANIFEST.json 逐项登记文件哈希，已逐成员验算。[包清单](../evidence/B/delegated_execution_2026-11-10/result_package.json)

解压结果包至 packet，再把 source_48157a8.zip 解压至相邻 source 目录。使用锁定 NumPy 2.1.3 的 Python 环境，在 source 中运行以下命令。输出目录应为新目录。

```powershell
python -m experiments.analyze_formal --manifest ../packet/frozen/manifest.json --run-index ../packet/batch/run_index.jsonl --output ../recomputed_analysis
```

已在无 Git 元数据的独立源码目录和离线安装的 CPU 运行环境中重新读取完整结果包，summary.json、paired_deltas.csv 和 failure_ledger.csv 均逐字节复现。[解压复现记录](../evidence/B/delegated_execution_2026-11-10/clean_package_reproduction.json)

结果完整性独立审查还核对了全部运行哈希、18×10×3 覆盖、540 行指标及实际代理身份。[库存结果复核](../evidence/B/delegated_execution_2026-11-10/C_result_audit.json)

机器可读 summary 中 formal_verdict 为未完成、result_signoff 为 pending，表示结果发布门禁仍待完成。C 接收本批统计时应保留授权代理复核方式、实际适用域、样本量及负结果，并按 claim 及材料签核流程发布。
