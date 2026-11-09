# WP2 独立审阅与一次修复记录

独立审阅范围0638428..fdf6bee。原结论无Critical、六项Important、一项诊断性Minor；审阅未代跑全库。六项Important均有对应失败记录，修复后定向与全库重新验证：

1. Job登记前孤儿等待：两条路径的gate等待改为检测父进程sentinel存活；真实父死回归覆盖登记前与登记后。
2. 状态异常杀死监控：失败状态兜底与逐run清理，monitor不被I/O/JSON异常终止；后续超时回归通过。
3. ZIP未核哈希：根/子manifest完整集合和SHA核验，使用已核bytes快照导出；坏产物/坏manifest回归。
4. 模型manifest缺信任锚：B登记已签收固定SHA，对同bytes做SHA与JSON格式验证。
5. 结构全mask误记成功：有任务且结构候选全禁用时NO_VALID_CANDIDATE回退；空队列及模型主动idle仍合法。
6. Linux zombie误认存活：读取/proc状态，Z/X视为已退出；Linux专属实进程回归在Windows跳过，作为平台未实测限制披露。

诊断项按原交接“缺包/损坏需可诊断”的要求处理：保留422/INVALID_CONFIG，并返回details.reason=MODEL_UNAVAILABLE。初次跨平台退出测试的30ms窗口不能保证Windows完成OS退出，退出场景改用1000ms预算，卡死场景仍测30ms；生产预算维持100ms。

未评判/未完成：模型泛化与收益、强优化器、正式矩阵、前端浏览器和换机、A/C接收人签收。这些属于后续任务，不由本轮修复推断通过。
