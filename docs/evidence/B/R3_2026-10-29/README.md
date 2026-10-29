# R3实际合成运行证据

本目录不是手工契约fixture。samples/{normal,multiblock,ack_loss,no_delivery}/均由backend.cli实际运行生成，保留完整配置、原始事件、结果、能量账本和源文件/产物哈希。使用synthetic健康和物理参数、显式manual动作脚本，未使用A模型或C页面。

最终验证：R3新增23项、R2 41项、全库242项通过；pip check通过。verification.json记录源提交、实际run_id、逐例数值与核验结论；local-log-index.csv记录本地RED/GREEN和全库日志路径/哈希，日志原件在runs/r3_2026-10-29/。

四例分别去重收到1024、2500、1024、0byte；最后一例J/bit为null/NO_DELIVERY。断窗例两次received只贡献1024byte，完整业务在1.03125秒已按时收到，最终能耗364J。详见交接单与docs/metrics.md。

status.json是完成状态依据，须结合manifest哈希完整性；存在results.json不代表运行完成。所有sample的源文件SHA及产物SHA在交付时已与当前源码/原始run核对。

执行日志保留实际生成字节（含Windows换行），由.gitattributes关闭文本规范化，避免克隆时Git换行转换破坏manifest哈希；其他JSON/JSONL按LF保存。

A/C尚未签收，本目录不能替代其独立验收。R3不证明统一guard、基线、教师、学习策略或API已实现；R2历史证据保持原样。
