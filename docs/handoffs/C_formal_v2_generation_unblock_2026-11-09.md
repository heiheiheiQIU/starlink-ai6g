# Formal-v2候选输入生成解阻单（C→A/B）

日期：2026-11-09

状态：`generation_receipts_complete_candidate_generation_authorized`

## 事实更正

C生成前原始回执已经完成，不应继续登记为“等待C回执”。

- 原始回执：`docs/acceptance/B_formal_v2_generation_C_2026-11-08.json`
- B归集镜像：`docs/evidence/B/sprint_2026-11-09/generation/C.json`
- A回执：`docs/evidence/B/sprint_2026-11-09/generation/A.json`
- B回执：`docs/evidence/B/sprint_2026-11-09/generation/B.json`

C于2026-11-09再次核对：A/B/C三份回执均为 `accepted`，三名reviewer不同，三份 `subject` 规范化内容完全一致。

## 当前授权边界

三份回执只授权B依据被冻结的 `formal_v2` 对象生成180条候选输入：

- 18个工况；
- 每工况10条轨迹；
- 种子600000—600179；
- 策略集合仍为EDF、Value、原始Learned；
- 不加入Hybrid，不替换模型，不修改统计协议。

该授权不等于：

- 候选输入已经通过第二阶段三方复核；
- 正式冻结已经完成；
- 540次策略运行已经获准；
- 任何AI效果结论已经成立。

## 冻结源码要求

C于2026-11-09现场重算发现：三份回执彼此一致，但当前 `feature/frontend` 工作树不是候选生成环境。

- 已签 `code_sha256`：`88e44ec10e33e7f15e81b335894762197d8aec95698e932b1ef314f894cc9889`；
- 当前C工作树重算值：`5bda7c996bbc3e5564f083d0dcfea0571ab72b3ddea0c539d757dfd8de7a4b16`；
- 其他subject字段均一致，差异仅为正式源代码集合哈希。

B必须在登记的正式源码提交上生成候选。对应修复提交为 `d039b98cb45a84a4fdaeaf4e4caa4595603cd1dc`；交接提交 `48157a8f4a1cdd7770685b79deb3fe4524b1bf7d` 相对该提交只增加证据和文档，没有修改 `backend/`、`training/` 或统计脚本。不得在后续sandbox或前端集成提交上直接生成。

## B立即动作

1. 在生成前subject对应的冻结源代码 `48157a8f...`（正式代码等价于 `d039b98...`）上重算subject，必须得到已签 `code_sha256=88e44ec...`；
2. 输出180条候选配置及manifest；
3. 运行现有 `backend.formal_v2.verify()` 和 `backend.formal_freeze.verify_candidate()`；
4. 生成post-generation来源/泄漏复核包；
5. 将候选manifest、复核包、完整SHA和复现命令交付A/C；
6. 等A/B/C候选输入回执齐备后再冻结和运行，禁止直接启动540次。

## A立即动作

1. 将“等待C原始回执”更正为“生成前三签已齐”；
2. B交付候选包后复核来源、划分、种子和泄漏隔离；
3. 不把Hybrid加入当前formal_v2。

## C立即动作

1. 使用 `scripts/review_formal_v2_candidate_c.py` 复核候选包；
2. 机器检查通过后仍进行人工来源和泄漏复核；
3. 只对实际审阅过的候选对象签署C回执；
4. 第二阶段三签前不授权540次运行。
