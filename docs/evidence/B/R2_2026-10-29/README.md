# R2首轮合成环境验证证据

日期：2026-10-29（Asia/Hong_Kong）。B-N2首轮，状态ready_for_review，待A复算和C事件消费确认。H00冻结基线main@75f1c52；实际短例运行的源码提交为39d7d11，逐模块SHA记录在sample/manifest.json。

## 已验证结果

- R2共41项测试通过；全库219通过、0失败、0错误（9.03秒）。全库包括117项H00合同及61项旧资产测试。
- 36W×100s=1Wh；E=0.1Wh时clip前-0.9Wh、clip后0；无当前窗口发送0byte；未来任务在到达前不可见。实际调用结果见[hand_checks.json](hand_checks.json)。
- 单块1024byte+32byte头、8192bit/s，发送持续1.03125s；2秒背景36W、发送36W，共消耗0.0303125Wh，最终9.9696875Wh。事件和账本来自实际执行，浮点末位误差按1e-12容差复核。
- 无ACK前保留inflight和剩余载荷；没有伪造received/acked或正式results.json。
- Observation与真实窗口/能量隔离，合成健康输入独立提供；过于乐观的健康估计不会被隐藏真值oracle“修正”，实际越界仍留证。
- 原backend/contracts.py、configs/schema.json、A/C代码和验收回执相对main未改；没有新增依赖。

## 实际短例交付给C

[sample/config.json](sample/config.json)、[sample/events.jsonl](sample/events.jsonl)、[sample/energy_ledger.json](sample/energy_ledger.json)、[sample/manifest.json](sample/manifest.json)是39d7d11实际运行后复制的原始四文件，样例产物及源码SHA逐一匹配。manifest标记synthetic/send_only_ack_pending、非卫星测量、非策略对比。

这些是实际执行的合成验证日志，既不是旧冻结预测，也不是手工合同fixture；它们仍不能证明新策略收益、在轨性能或完整ACK闭环。没有将该短例包装成正式完成的RunResult。

## 验证命令与日志

```powershell
New-Item -ItemType Directory -Force runs/r2_2026-10-29 | Out-Null
.\.venv\Scripts\python.exe -m pytest -q --noconftest -p no:cacheprovider --basetemp=runs/r2_2026-10-29/tmp-full-reviewed --junitxml=runs/r2_2026-10-29/full-reviewed.xml
.\.venv\Scripts\python.exe -m backend.simulator.engine --config configs/scenarios/minimal.json --output runs/r2_2026-10-29/demo-final
```

复跑使用新的临时/输出目录。当前全库XML中41项来自test_simulator.py，其余178项来自main已有测试。原始日志/测试XML在本机被忽略的runs/r2_2026-10-29；local-log-index.csv记录路径、大小和SHA，不等于已上传所有日志。

## 先失败后实现与修复

1. 原语测试先因模块不存在而失败；实现能量/窗口/队列后16项通过。初次手工测试把t=10时arrival=5的任务误称未来，已更正为arrival=15；未为迁就错误测试修改生产逻辑。
2. engine测试先出现22失败、16通过（缺少engine模块）；随后实现明确合成配置、observe/step和导出，包含额外oracle隔离检查后39项通过。
3. 时钟过小dt不能推进的回归先失败，增加受控拒绝后40项通过。
4. 独立审查发现分段终点ULP超前会提前读取健康观测。新增反例先失败，统一终点后本阶段41项、全库219项通过。详情见[review.md](review.md)。

## 参数、范围与下一步

参数台账configs/parameters.csv逐项给单位、synthetic/协议假设来源与敏感性范围；无设备功耗或真实链路预算测量。R2只接受真实误包率0、每run单策略，不生成随机场或多策略指标。

R3仍需实现ACK/超时重传、去重、跨步传输、正式业务成功评价及完整run产物。A的新HealthCoreEstimate尚未混入R2；H01正式适配须单独交B验收。接收流程见docs/handoffs/B_N2_R2_2026-10-29.md；本轮不代A/C签收、不自动合入R2。
