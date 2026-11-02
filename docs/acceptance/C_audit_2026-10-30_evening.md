# C 审计注记：2026-10-30 晚间新推送（A-N3 数据管线 / B seed与溯源修复 / B对C复核）

日期：2026-10-30 深夜。对象：`origin/feature/ai@866df43`、`origin/feature/shared-channel-r5@d68d3cb`。方式：代码与证据审查；未修改 A/B 分支。

## 1. A-N3 数据管线（866df43）：符合批准范围①-④，等待B训练门

| 项 | 结果 |
|---|---|
| ①H02 独立签收 | ✅ H02_A_2026-10-30：20条源观测**独立重算标签**（非拷贝信封），20 OPTIMAL/0失败/0不合格，标签实现 542096f、切分实现 882b1f6 锚定 |
| ②20场景审计 | ✅ 产物哈希与manifest全数复算一致（samples/summary/manifest/splits 四个SHA-256，最终修复后字节不变、未再生） |
| ③特征/mask | ✅ policy_features.py 只用公开 Observation 字段；candidate mask 结构规则（inflight/过期/剩余0屏蔽，idle恒可）；输入强制重校验+有限数检查；截止差保留符号 |
| ④按scenario_id划分 | ✅ 12 train/4 val/4 test，样本与场景双维度交集为空、覆盖完整 |
| 失败净化 | ✅ 2deb485：异常文本受控化、config字节快照哈希化、RED→GREEN 双向验证 |
| 纪律 | ✅ training_enabled=false，未训练、未声称性能；定向87过/全库380过（1条已知Starlette弃用警告） |
| 门禁 | ⏳ 按批准流程，**B 于 10/31 上午按 `A_training_gate_B_checklist` 验收样本与切分**；训练截止 11/02 22:00 不变 |

## 2. B seed透传与溯源修复（d68d3cb）：P2关闭

- **35b37ea**：service 校验 config.seed==request.seed（不一致422），worker 以 `dict(request.config, seed=request.seed)` 传入两子运行——H03 审计发现的"顶层7/子层0"问题关闭（含34行API新测试）；
- **921a24b**：发行副本根无 .git 时**显式失败**进入 honest fallback——修复了"副本嵌套在父git仓库内时 rev-parse 上溯读到父仓库HEAD"的溯源冒名隐患（M-04修复的补丁）。两者均复核通过。

## 3. B 对 C 的复核（C_N1_N2_B / H01_B）：回执要点

- C-N2 合同镜像 accepted_with_notes：27结构字段名集合全一致，语义边界逐项复核；B 独立跑 npm test 39过、构建过（47 modules）；
- **锁文件注记的回应**：B 复核对象 a1375b1 早于 C 的 pnpm 冻结（44656e8）。C 的锁文件是 **pnpm-lock.yaml**（lockfileVersion 9.0），复现命令 `pnpm install --frozen-lockfile`；B 的 npm 路径是有效的交叉验证，但**不可作为冻结复现路径**——此为工具链版本差，非缺陷，记录于此以免歧义；
- H01 主验 accepted_with_notes：158定向过＋真实CLI两命令核验＋未来记录/raw_fraction拒绝测试；**A-N1 至此三方闭环（A交付+B主验+C复核内部核心）**；
- C-N1 设计文档 accepted_with_notes（限后端接口与证据语义）：learned/Observation/assistant 接口须另行合同——同意，已列入后端接口需求。

## 4. 裁定

- A-N3 数据管线：C 侧认可（范围①-④达成）；**训练闸门归 B（10/31 上午）**，C 不越权签训练门；
- B seed P2：关闭；溯源修复：通过；
- A-N1：三方完成；A-N3 训练：11/02 22:00 截止不变。
