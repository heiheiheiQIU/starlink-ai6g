# C 对 formal_v2 生成前冻结对象的复核回执 · 2026-11-08

## 裁定

`accepted`。仅批准 B 按已签对象生成180条 formal_v2 候选输入；不批准冻结正式输入、不批准启动540次策略运行，也不构成任何效果结论。

审核对象：

- B 修复代码：`d039b98cb45a84a4fdaeaf4e4caa4595603cd1dc`；
- B 交接提交：`48157a8f4a1cdd7770685b79deb3fe4524b1bf7d`；
- `subject.json` SHA256：`936e5b2186bf6f0c65e10a3001b887d492ac85ffb54e65ced73ad72aad9346fe`；
- 可机读回执：`docs/acceptance/B_formal_v2_generation_C_2026-11-08.json`。

## 独立复核证据

1. 使用冻结版本 NumPy 2.1.3、pytest 8.3.5、Pydantic 2.12.3，独立复跑 `tests/test_formal_v2.py`：`7 passed`。
2. 三类签核后篡改——核查脚本、A-N3划分、A-N4b来源划分——均在进入输入生成前被拒绝。
3. 现场重算 `backend.formal_v2.subject()` 与提交的 `generation/subject.json` 完全一致；C模板绑定同一subject。
4. 预期输入为18工况×10轨迹：180个唯一种子、180个唯一内容哈希、180个唯一配置哈希、180个唯一输入哈希；种子范围600000—600179，已登记交集为空。
5. 策略集合严格为EDF、Value、Learned，对应540个唯一策略运行键；本复核未生成候选输入、未运行任何正式策略。

## 边界与后续门禁

- `claim-A1`、`claim-X1/X2/X3`继续保持`pending`；
- A-N4b继续封存，不训练、不替换旧冻结模型；
- B收齐A/B/C生成前回执后方可生成候选输入；
- 生成后仍需A复核来源与划分、B复核运行与统计对象、C复核180条实际清单、共享输入及SHA；第二阶段三方回执未完成前不得冻结或运行。
