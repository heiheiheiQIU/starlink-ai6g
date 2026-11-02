# C 审计注记：A 修复版（1c90246）+ R2/R5 回执（ddcca9c）

日期：2026-11-02 晚。C 独立复核如下。

## 1. 坏ZIP修复（d97ff5b）：与我此前建议完全一致

- except 元组新增 `zipfile.BadZipFile, EOFError`（**包含 C 补充的 EOFError 建议**）→ 统一转 `LearnedPolicyError(MODEL_FORMAT)`；
- 回归两条：真PK签名坏容器＋**截断npz**（C 建议的同类缺口）——A 修复前 2 failed、修复后 2 passed（RED→GREEN 自证）；
- 模型五文件与运行/训练配置 SHA 未变（无需重训成立）；组合定向 94、全库 503；
- C 逐行核对 diff 无夹带，修复口径正确。

## 2. R2 四项手算回执（B_N2_R2_A）：合格，且 C 复算数字吻合

A 五组独立手算全部与实现一致：空闲能耗 1Wh→剩余9.0Wh、无窗口拒绝 sent=0、负能量裁剪前留证（-0.9→0.0 含 ENERGY_BELOW_ZERO）、到达因果（t=0不可见/t=5可见）、发送能量 0.0303125Wh（C 复算：(36×2+36×1.03125)/3600=0.0303125 ✓，传输时长 (1024+32)×8/8192=1.03125s ✓）。41定向/219全库；探针误用 task_001 的更正如实记录。

## 3. R5 公平性回执（B_R5_A）：合格，聚合数与 B 汇总一致

- 公平性核心复核：`uniform_at` 键=version|seed|stream|time_index，无策略/任务/块/模式参数；A 以 seed=10000、t=0.3 复算 data=0.9851563699059169（两次一致）、ack=0.9042886041986345；
- 360行重组：180轨迹各含 edf/value 两行，cell_id/seed/run_id/input_hash 组内一致 0 异常；per_run.csv 与 summary.json SHA 与 manifest 一致；
- 独立重聚合：EDF 均值 0.4869152046783626 / value 0.553192007797271——**与 C 前端实验矩阵页展示的同一批真实数据一致**；
- 5 条非阻塞边界如实（非训练划分、robust/fast共用随机数、零负段≠保储备、无AI结论、教师非零损失 UNSUPPORTED_LOSS）。8+1定向/303全库。

## 4. 裁定与门禁状态

1. **PR #8 修复：C 侧认可**，等 B 复验升级签收（B 今晚/明早）；
2. **main 合并三项前提至此全部满足**（C B1 accepted、A R2 accepted、A R5 accepted_with_notes 非阻塞）——**R2→R5 依序合 main 只欠 B 执行**；
3. 时间警示：G4（11/04）前剩余 = B 验包签收＋learned 接入＋正式实验，**窗口已压到 1.5 天**，B 必须今晚开动接入，A 待命配合正式实验配置。
