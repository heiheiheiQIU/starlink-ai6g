# B-N3 真实本机 HTTP 验证

源代码为 cccca9892086522624a5979216d7a2ab73209803。实际启动127.0.0.1上的Uvicorn服务，经HTTP提交edf/value比较，读取状态、22页共64条事件、结果和ZIP，并核验ZIP结果与GET一致。记录见http-check.json，原运行目录副本见run/；输入和全部指标均为合成规则验证。

five endpoint responses: POST 202，status/events/results/export 200；不存在404，重复策略422。409、429、崩溃、超时、重启恢复、Windows读锁和目录联接导出边界另由tests/test_api.py的真实进程/故障测试覆盖。

导出ZIP保存在本机runs/b_n3/live/export.zip（不入Git），其SHA已记录在http-check.json。run/保存ZIP中的允许列表内容，manifest中逐文件哈希可复查。server.log、JUnit日志用于验证，可能包含测试环境路径，不属于API导出包。

这是ready_for_review的B交付，不含C页面联调、A学习模型或性能优越性结论。接收步骤见docs/handoffs/H03_api_2026-10-29.md。
