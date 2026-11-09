# H00独立代码审查与修复记录

2026-10-28。审查由独立代码审查代理完成，非作者自检，也非A/C验收。审查范围为相对70c5064的公共类型、schema、契约测试、fixture及依赖变更。

## 发现

P1：默认revalidate_instances=never使已有模型实例绕过字段重验。审查者复现：

- Task子类添加received_at_gateway后可以留在Observation.tasks，策略读取到接收端真值。
- 已创建Task的remaining_bytes改为-1或data_location改为ground，再传入Observation仍被接受。

审查者对完整评分约束、延迟转换、事件变体、分页、缺失指标和fixture非实验标记未提出其他重要问题。其当时测试读取并发更新中的73项；最终结果以修复后的验证日志为准。

## 修复与证据

- 公共ContractModel启用revalidate_instances=always，对嵌套已有对象重新验证。
- 回归 `test_existing_model_instances_are_revalidated_at_contract_boundary`：破坏已有健康模型下界的实例必须拒绝。
- 回归 `test_observation_rejects_truth_bearing_task_subclasses`：携带隐藏接收真值的Task子类必须拒绝。
- 两项先失败，见runs/h00/revalidation-red.log；修复后75项契约通过，隔离快照全库136通过。主仓库25项旧资产路径失败/错误仍单列，未掩盖。

对象仍不是深度不可变容器或安全沙箱。边界必须调用model_validate，环境R2须构造独立观测，不能在验证后附加隐藏真值或共享环境可变对象。此限制已进入合同说明。

结论：该重要代码问题已修复；不替代A/C对字段细化和使用接口的实际签收。
