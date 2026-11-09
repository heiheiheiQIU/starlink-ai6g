# B 正式候选交接 · 2026-11-09

状态为 candidate_pending_review。已同步 C 的 8556ead 和 A 的 a261a34，三份生成前 accepted 回执已核实，实际候选审核包已交付。B 的技术核查为 accepted_with_notes，等待 A/C 对实际候选及来源完成第二阶段签核。

## 实际执行与证据

- 生成执行提交为 `48157a8f4a1cdd7770685b79deb3fe4524b1bf7d`。全新 detached 工作区再次生成，subject 与三份原始回执逐项一致，code_sha256 为 `88e44ec10e33e7f15e81b335894762197d8aec95698e932b1ef314f894cc9889`。
- 18 工况每格 10 条，共 180 条，种子严格为 600000–600179。trajectory_id、seed、config_sha256、input_hash、content_hash 五类各有 180 个唯一值。每条轨迹的 EDF、Value、原始 Learned 使用相同配置，共 540 个规划运行键。
- 候选清单 SHA256 为 `2b0814db44b7c70cd94e44608e34c762ffaa86969ea6f955e4736b7b3cdcd31f`。重新生成的 182 个文件与交付包逐字节一致，复验见 [冻结提交重生成记录](../evidence/B/formal_v2_candidate_2026-11-09/frozen_commit_regeneration.json)。
- 与退役、开发和 A-N4b 的 390 个不同种子、374 个不同内容哈希均无交集，与旧教师的 20 个初始公开观测投影也无交集。旧教师缺少完整种子，来源组及划分仍由 A 复核。[B 实际检查](../evidence/B/formal_v2_candidate_2026-11-09/B_inspection.json)
- 原有两个候选核验入口通过，C 的审核工具通过并输出 machine_verified_human_pending。C 工具测试 7 项通过，冻结代码的候选、冻结、运行与统计回归 63 项通过。[机器审查输出](../evidence/B/formal_v2_candidate_2026-11-09/C_machine_review.json)

## A/C 接收入口

候选独立分支为 `codex/b-formal-v2-candidates-20261109`，其首个交付提交为 `749872000c73f2d6eabb2cd3fd51e925f6962b49`。最新补充包含重新生成证明、C 机器核查和 B 技术回执。当前集成交接分支 `codex/b-formal-handoff-20261109` 同时包含 C 最新产品代码和相同候选包。

打开 [候选包说明](../evidence/B/formal_v2_candidate_2026-11-09/README.md)、[完整轨迹清单](../evidence/B/formal_v2_candidate_2026-11-09/candidate/manifest.json) 和 [来源复核草稿](../evidence/B/formal_v2_candidate_2026-11-09/review/leakage.json)。每份原始配置可由清单中的 config_path 取得，全部模型、代码及统计 SHA 见 [binding](../evidence/B/formal_v2_candidate_2026-11-09/review/binding.json)。

A 核查来源和划分，C 核查实际清单及共享输入。完成后共同确认最终 leakage.json 的字节和 SHA，再由三方把该 SHA 填入各自正式冻结回执。B 的 [技术回执](../evidence/B/formal_v2_candidate_2026-11-09/B_technical_receipt.json) 已说明本方检查结论，工具使用的 review/B.json 等待绑定最终 leakage SHA。三方回执通过索引与冻结工具后，B 才能进行正式预跑、记录容量估算并执行 540 个唯一运行键。

核验和冻结工具应在独立检出的 48157a8 上运行，证据包可以使用外部绝对路径。示例复验命令如下。

```powershell
& $python -m backend.formal_v2 --verify "$packet/candidate/manifest.json"
& $python -m backend.formal_freeze --help
```

## 离线来源校正

修正版位于 `runs/B_sandbox_offline_20261109_provenance_fixed.zip`，24,845,119 bytes，SHA256 为 `4f7adba93abb8315af4f30017d029d523c82947f6c4cebebd29854b8df945028`。已从 source.zip 移除过期 offline_package.json，并同步其内部证据索引。包根 SOURCE_PROVENANCE.json 记录原包身份及变更路径，根 SHA256SUMS.json 已重算。逐项通过外层和内层哈希核验，运行源码、模型配置及前端文件与原核验包字节一致。[校正记录](../evidence/B/offline_provenance_fix_2026-11-09/verification.json)

历史原包保留，取包时使用上述修正版。它承接此前版本的沙盒交付，最终 C 前端的发布包和另一台机器验收由后续发布流程完成。

## 当前边界

正式策略运行数为 0，正式统计结论 pending。原始 Learned 及其 S1/S3 零交付证据继续保留。前一轮本地 Hybrid 实现草稿已存入 Git stash，标记为 Paused guarded development per B formal priority 2026-11-09，当前交接分支仅交付已签协议要求的策略及候选证据。
