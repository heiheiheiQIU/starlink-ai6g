# C 审计注记：WP5 正式输入候选（PR #13，710f141）

日期：2026-11-05 晚。对象：`origin/codex/b-formal-inputs-20261104@710f141`。C 代码级复核。

## 1. 生成管线复核：通过，工程水准高

- `backend/formal_inputs.py`＋`experiments/formal_v1/protocol.json`（formal-input-protocol-v1）：18工况×10轨迹=180独立输入；种子段 200000-200179，**显式排除旧开发种子 10000-10179**；
- 测试覆盖到位：双次物化逐字节一致（确定性）、180×{trajectory_id/seed/input_hash/content_hash} 全唯一、每工况恰10条、旧种子混入拒绝（old_seed 用例）、篡改拒绝（config/manifest/路径穿越三用例）、pending 门禁（require_frozen 在 model=null 时拒绝）——**发布前无法把"未定模型"的输入冒充冻结产物**；
- manifest 登记生成器与合同/仿真全源码 SHA＋每轨迹 config/content/input 哈希——与我们的 claim 唯一事实源纪律同构；
- 参数：负载 2/6/10 任务×2048B、期限格 8/12/18/24s、能量 0.8/1.2/10Wh、mild/strong 丢包剖面；健康假设（初始精确、保守传播、RUL缺失）如实登记。

## 2. 一个必须写进材料的诚实事实（C 重点提示）

**protocol.json 自述 `training_domain: "All cells have nonzero forecast data loss, outside current deterministic teacher labeling domain"`**——正式实验全部工况带随机数据丢失，而 learned 冻结包（以及 B 支持域下的 A-N4b 首批）是在零损失域训练的。含义：

1. 正式实验本质上是 learned 的**域外评估**——这合理（真实化），但进一步压低 learned 的预期表现；
2. 据此修正我此前的赢面评估：部分工况显著赢 40-55% **下调至 20-35%**；总体"等效或负"的概率上升；EDF 显式回退机制将成为 learned 在多数工况的实际行为——这本身构成第5.5节"域外行为与回退占比"的现成素材；
3. 材料口径建议：learned 声明加"训练域为零损失合成设定；正式环境含随机丢失，属域外评估"——**不允许任何"域外劣势"事后改口径**。

## 3. 门禁状态

- `model: null`＋pending 门禁：管线已就绪，等 A-N4b 验包（或旧冻结包）落位；
- **A-N4b 来源交集检查仍待 A 交付**（manifest 注明 pending_A_N4b_delivery）——A 交包时必须附带种子命名空间与正式段（200000-200179）无交集的证明；
- 已知小项（冲突报错缺轨迹信息）非阻断，记录在案。

## 4. C 裁定

- WP5 第一项：**C 复核通过**（生成管线、确定性、防篡改、pending 门禁均代码级确认）；
- 正式运行入口＋统计分析为 B 的下一项；模型落位与冻结以 11/06 20:00 为硬线；
- 时间警示：当前 11/05 20:26，**A-N4b 尚未推送**——若明早仍无交付，直接走旧冻结包路径，不再等待。
