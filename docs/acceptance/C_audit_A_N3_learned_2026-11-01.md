# C 审计注记：A-N3 learned 评分器交接（codex/a-n3-learned@97124d4，未推送）

日期：2026-11-01 午后。方式：交接单逐项审查＋远端状态核对（分支未推送，代码级复核待推送后进行）。C 不代 B 签验收，本注记供 B 主验与任务板使用。

## 1. 交接单质量：完整且纪律到位

| 验收门（B冻结时列出的交付项） | A 交接 | 评估 |
|---|---|---|
| score_actions 入口 | `backend.policies.learned.score_actions(observation)`，覆盖完整候选键集，结构不可执行候选赋 -1.0 掩码分 | ✅ 表述完整 |
| 权重SHA/model_card/归一化来源 | 五文件 SHA 表＋训练证据 verification.json；归一化只拟合 train | ✅ |
| 特征/动作版本 | policy-features-v1，23维（14全局+9候选） | ✅ 与冻结特征一致 |
| 推理耗时 | 冷加载2.63ms；1000次warm median 0.52ms/p95 0.68ms/max 1.16ms | ✅ 实测记录 |
| 回退约定 | LearnedPolicyError→ScorerGateway 100ms超时/异常回退；MODEL_UNAVAILABLE/MODEL_TIMEOUT | ✅ |
| 诚实边界 | test MSE 0.356/feasibility acc 0.667 只作冻结行为记录，**明确不称泛化/优于基线** | ✅ 无夸口 |
| 身份复核 | 四SHA相对基线2cfe89c无差异（未动合同/旧数据/legacy/B-C接口） | ✅ |

模型本身：23-32-16 MLP、sigmoid utility+feasibility logit、三种子训练按最低val loss选20261033、train MSE 5.8e-11（小样本可学习性达成——12/12 optimal-set hits）。

## 2. 唯一阻塞：B API status.json Windows 文件锁

- A 全库 498 过一轮；最终复跑 497 过/1 失败，失败点= `RunService.status()` 读 status.json 偶发 PermissionError；连续复跑第 5 次复现；A 未改 B 的 API（角色边界正确）；
- **定性**：与 B 此前修过的同类问题同源（worker.py 已用 read_text 有界重试，service.py 的 status/reap 读取路径未全覆盖）——**B 修复范围小**：把 status.json/各状态读取统一走带重试的 read_text，约半小时；
- A 的处理正确：不推送、不合并，等 B 修复后拉取复跑再推 PR。

## 3. C 裁定与后续

1. **A-N3 交付形态合格**（A侧 ready_for_B_review 成立）；C 不代 B 验收；
2. **B 今晚必须**：①修 status.json 读取锁（小修+回归）；②按交接单6项独立验收模型包（SHA/manifest/npz allow_pickle=False/定向复跑/20观测复算/故障注入回退）；
3. A：B 修复后拉取→全库复验→推送→建 PR；**11/02 22:00 截止仍可守**（B今晚修+明早验收，A明早推PR）；
4. 提醒 A：**main 合并的两份欠账回执**（R2四项手算、R5公平性）还没交——PR 之后立即补，否则 B 合 main 还是被卡；
5. C 侧：A 推送后我复核代码与冻结包哈希（与交接单五SHA对照）。
