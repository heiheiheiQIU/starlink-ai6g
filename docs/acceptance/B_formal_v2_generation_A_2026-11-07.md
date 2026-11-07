# A 对 formal_v2 生成前冻结对象的复核回执 · 2026-11-07

## 裁定

`accepted`，仅批准 B 按已签对象生成 180 条 formal_v2 候选输入。正式输入尚未生成，540 次策略实验尚未运行，本回执不构成实验结果签收。

审核对象：

- B 修复代码：`d039b98cb45a84a4fdaeaf4e4caa4595603cd1dc`
- B 远端交接：`48157a8f4a1cdd7770685b79deb3fe4524b1bf7d`
- 新版 `subject.json` SHA256：`936e5b2186bf6f0c65e10a3001b887d492ac85ffb54e65ced73ad72aad9346fe`
- 可机读 A 回执：[B_formal_v2_generation_A_2026-11-07.json](B_formal_v2_generation_A_2026-11-07.json)

## 独立复核证据

- 冻结、生成与三种签后篡改门禁：`25 passed`。
- A 数据、划分、训练、Learned 策略与接口：`179 passed`，仅有既有 AnyIO 弃用提示。
- 新版 subject 与 B 的 A 模板语义完全一致。
- 核查脚本、A-N3 `splits.json`、A-N4b `source_splits.json` 的现场 SHA256 均与 subject 一致。
- A-N3 训练/验证/测试为 12/4/4，样本、场景、Observation 内容和来源组两两无交集。
- 预登记 `600000–600179` 共 180 个唯一种子；独立构造得到 180 个唯一内容哈希。
- 与旧开发矩阵、`engineering_regression_v1`、A-N4b 场景及旧教师公开 Observation 的交集均为 0。

## 边界

- A-N4b 保持 `blocked_diagnostics_verified`、`training_enabled=false`，不得用于训练或替换冻结模型。
- 正式实验继续使用已冻结的 `a-n3-mlp-v1`；其模型卡限制仍有效，不主张泛化、策略优越性、成熟优化器、真实卫星或在轨效果。
- `claim-A1`、`claim-X1/X2/X3` 继续保持 `pending`。
- 生成 180 条输入后，A 仍须对实际候选执行第二阶段来源、划分及内容交集复核，未完成第二阶段回执前不得冻结或启动 540 次正式运行。
