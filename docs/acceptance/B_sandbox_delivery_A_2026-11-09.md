# B 沙盒离线交付 · A 独立复验回执

日期：2026-11-09  
验收角色：A  
裁定：`accepted_with_notes`

## 1. 验收对象

- 交接单：`B_sandbox_delivery_2026-11-09.md`；
- 附件：`B_sandbox_offline_20261109.zip`；
- 附件实际SHA256：`d637e638fcf1cf7baa4c178e3843afbd4847d85102df68ea2f6ef8d7ac08dc34`；
- 附件实际大小：`24,845,651` bytes；
- 外层说明登记源码：`71c40b0842ac9547895874288a1633d1f4fdb5ac`；
- 功能提交：`3bd22a30d864eb0bdd0a32b8efea426e1673b803`；
- 并发清理修复：`3f09926e78478c0ec235117d70fa605406977078`；
- 正式基线保持：`48157a8f4a1cdd7770685b79deb3fe4524b1bf7d`。

## 2. 独立复验结果

1. 附件SHA256与字节数均和外层交接单一致。
2. 外层 `SHA256SUMS.json` 登记的51个文件全部独立复算一致。
3. 唯一沙盒编译入口 `compile_sandbox_axes` 存在并输出完整 `RunConfig`。
4. 八个沙盒轴及顶层seed/policies均由后端校验；非法档位、负reserve、reserve超过20Wh、非法seed、额外字段均被拒绝。
5. S2与健康对照除health轴外一致；健康差异真实进入公开Observation、冻结评分和Guard，A2机器门禁通过。
6. S3真实出现 `ACK_LOST_CHANNEL`、`ACK_TIMEOUT`、同块重传和 `DUPLICATE_BLOCK`；S3重复运行在排除run_id与实测决策延迟后语义一致。
7. A在附件源码上独立运行五组定向测试，结果为 `54 passed, 1 warning`。

## 3. 运行裁定

| 对象 | 裁定 | 说明 |
|---|---|---|
| A2健康差异机器门禁 | `accepted_with_notes` | 评分和Guard均变化；Learned最终动作仍为idle |
| S1/S2/S3沙盒机制 | `accepted_with_notes` | 真事件、真哈希、真结果；不是正式实验 |
| S3协议闭环 | `accepted_with_notes` | 重传与去重归协议，不归AI |
| Learned效果 | `negative_observation` | S1/S2/S3均无Learned交付，必须原样保留 |
| 180条正式输入 | `candidate_reviewed_by_A_with_notes` | 三份生成前回执已齐；候选已生成并完成A来源/划分复核，最终三方冻结回执仍待签 |
| 540次正式运行 | `pending` | 未获授权、未执行 |
| formal效果claims | `pending` | 不得提前填写胜/等效/负结论 |

## 4. 来源备注

附件内部 `source/docs/evidence/B/sprint_2026-11-09/offline_package.json` 记录的是旧包：SHA `36de40f1...`、`24,770,339` bytes、source `3f09926...`；它与本次附件的外层SHA、字节数和源码标识不一致。

当前附件本体与外层交接单、外层逐文件清单相互吻合，因此该问题不推翻沙盒语义验收；但旧JSON不得作为当前附件的来源证明。B归档时应删除、重命名为历史收据或显式标记 `superseded`。

2026-11-10补记：B已登记修正版离线包 SHA `4f7adba93abb8315af4f30017d029d523c82947f6c4cebebd29854b8df945028` 及校正记录，但该修正版包体未随本轮A复核进入工作区，因此A只确认“校正记录存在”，不声称已独立核验修正版包体。

## 5. 后续门禁

1. A/B/C三份原始生成前回执已核实并绑定同一subject；180条候选也已生成。
2. A已完成来源、划分及泄漏边界复核；A/C仍须共同确认最终 `accepted` leakage字节，A/B/C再绑定同一个最终SHA。
3. 只有候选清单、模型/代码/统计规则及三方正式回执全部冻结后，B才能启动540次正式运行。
4. 正式运行必须保留Learned为idle、等效或负的真实结果，禁止重跑挑选。
5. 当前回执不批准Hybrid新策略进入formal，也不授权替换旧冻结模型。
