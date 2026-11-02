# C 复核注记：A-N3 数据阶段 changes_requested（B门）独立确认

日期：2026-10-30 深夜。B 对 `feature/ai@866df43` 的数据阶段验收结论为 changes_requested（阻塞：相同观测跨集合）。C 独立复现其核心证据如下。

## 独立复现（不依赖B的脚本）

对 `data/teacher/a_n3_20/samples.jsonl`（20条）按 B 口径处理：每条 Observation 仅去除 `run_id`/`policy_id` 两个标识字段，其余字段原样、规范JSON比较：

- **唯一观测 = 12 种**（20条样本中8条与其它样本内容完全相同）；
- **跨集合重复组 = 5 组**，与 B 回执表格逐条一致：

| 组 | 集合 |
|---|---|
| r4_01 / r4_13 | train / validation |
| r4_02 / r4_14 | test / train |
| r4_03 / r4_15 | train / validation |
| r4_05 / r4_17 | train / validation |
| r4_07 / r4_19 | test / validation |

## C 裁定

1. **B 的 changes_requested 成立**：A 的20样本来自B的20条preflight初始状态，其中8对内容相同（仅run_id/policy_id不同）；按scenario_id形式划分虽交集为空，但**不构成数据独立**——训练集与验证/测试集出现完全相同的决策输入，泛化评估会被污染。此问题必须在训练前修正。
2. 同意 B 的三条修正要求：同源/同内容整体归组或生成真正不同的新场景；新增忽略无关标识的重复观测与跨集合重复回归；新提交给出完整SHA与全部新产物哈希（旧文件留历史不回填）。
3. B 的 122 项定向通过与标签全数复算一致**不因此作废**（标签管线本身可信）；受影响的是划分与"独立场景"声明。
4. **B1 seed/ZIP/哈希复核**：B 的新入口 `scripts/verify_seed_p2.py` 尚未推送（远端 shared-channel-r5 仍为 d68d3cb），C 的重跑回执待 B 推送并绑定新 SHA 后出具；B 本地全库309过的记录仅作参考。
5. 扩样与接口对齐稿（B_training_scale_interface）：合理（支持域矩阵、同源先划分再派生、UNSUPPORTED不凑数、缺RUL保持null）；**确认责任在 A**，A 回复后 B 冻结批量格式。
