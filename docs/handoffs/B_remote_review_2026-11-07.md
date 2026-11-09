# B 远端复验与正式输入交接 · 2026-11-07

**当前状态为 B 已推送，等待接收人代码级验收。** 正式实验为“未完成”。正式输入、统计结果和换机复现分别签收。独立分支为 `codex/b-final-sprint-review-20261107`。

## 本次重新签核

审核代码提交为 `d039b98cb45a84a4fdaeaf4e4caa4595603cd1dc`。生成前 subject 新增三项逐字节 SHA256，生成与冻结复核均重新计算。生成后的来源审查包保存三份文件的副本，并与生成前回执逐项比对。

| 生成前覆盖文件 | SHA256 |
|---|---|
| `scripts/prepare_formal_v2_review.py` | `50e4090fec611906eae58f7255fe5e1649d240e3211e7117ae150c9a9c611628` |
| `data/teacher/a_n3_20_v2/splits.json` | `8826732869e9452d2f8e59889240b034e393d7c748429f3dc1020cf90967d1f8` |
| `data/teacher/a_n4_pilot_v1/source_splits.json` | `aaa5c558c83e9d2dcec0c9637f74dc5dc431de9109874a85f17cba2eb87c2e95` |

新版 [subject.json](../evidence/B/formal_v2_review_2026-11-07/generation/subject.json) 文件 SHA256 为 `936e5b2186bf6f0c65e10a3001b887d492ac85ffb54e65ced73ad72aad9346fe`。A/B/C 使用同目录对应角色的新版 pending 模板，在各自审核副本中填写回执。上一版 `58c68b6` 的回执需重新审核。

接收人可执行 `python -m pytest tests/test_formal_v2.py -k reject_changed_audit -q --basetemp runs/receiver_hash_test`。三种测试各自只改一份文件，保留原回执，检查生成器拒绝且输出目录不存在。有效用例使用独立的替代种子段。

本次全库 704 项通过，1 项 Linux 专用测试跳过，1 条既有 AnyIO 弃用提示。正式输入等待三方新版回执。[本次全库日志](../evidence/B/formal_v2_review_2026-11-07/audit_hash_full.log) · [篡改复现](../evidence/B/formal_v2_review_2026-11-07/audit_tamper_red.log) · [修复验证](../evidence/B/formal_v2_review_2026-11-07/audit_tamper_green.log)

| 复验对象 | 完整提交 |
|---|---|
| 原 B 三项问题修复及 697 项日志 | `03cbb225d46472d9bbbfdc463a6bad291fc2c04e` |
| B 干净环境和接口交付 | `f6da70e30b835aad2420602014b6d3039c6fe246` |
| 已接收 A 事实审核和图件修订 | `c3da9234cfd229bc81241a89e8e3a5ee54f5d450` |
| B 新旧轨迹隔离、生成前签核 | `c9ed2356b66906af33d8626feb57eb91bfdaf6ff` |
| 含生成后来源核查工具的代码版本 | `732ef8f92d1e83c18f4df23f0afa444f49e30c8a` |

接收人可在空目录中独立克隆，或在已有仓库只 fetch 并检查对象。以下命令用于已有仓库。

```powershell
git fetch origin codex/b-final-sprint-review-20261107
git rev-parse FETCH_HEAD
git cat-file -t 03cbb225d46472d9bbbfdc463a6bad291fc2c04e
git merge-base --is-ancestor 03cbb225d46472d9bbbfdc463a6bad291fc2c04e FETCH_HEAD
```

## 代码级复验材料

| 曾复现的问题 | 修复行为 | 回归用例 |
|---|---|---|
| 来源文件可缺失，来源审查可在 A/B/C 回执生成后被替换 | 读取并校验每个来源文件，随冻结包保存。每份角色回执绑定同一份 leakage 文件 SHA | `test_source_evidence_and_receipt_binding_enforced` 的 missing_source、source_tampered、leakage_replaced |
| 评价终点从 24 秒改为 2 秒仍能计为完成 | 逐次将运行配置、策略及模型、评价终点与冻结配置比对，再验证运行配置和源码 SHA | `test_runner_rejects_actual_horizon_different_from_frozen` |
| 缺少 Git 可执行文件导致冻结失败 | 检查发布根的 Git 元数据，缺少 Git 时使用源码哈希并保留空 revision | `test_freeze_without_git_executable` |

三项问题的原始失败和通过日志在 [review_red.log](../evidence/B/sprint_2026-11-07/review_red.log) 和 [review_green.log](../evidence/B/sprint_2026-11-07/review_green.log)。历史后端及报告测试为 **697 passed、1 skipped、1 warning**，前端 **77 passed**，TypeScript/Vite 构建通过。唯一跳过的是 `tests/test_inference_lifecycle.py::test_linux_zombie_is_not_reported_alive`，检查 Linux 僵尸进程状态，需要 Linux 运行环境。警告来自既有 AnyIO 弃用提示。[697 项原日志](../evidence/B/sprint_2026-11-07/final_suite.log) · [77 项与构建原日志](../evidence/B/sprint_2026-11-07/frontend_check.log)

当前复验命令如下。全库需要 README 所列旧资产布局和材料测试依赖。`--basetemp` 使用新目录。新增 4 项检查覆盖旧矩阵禁入、缺签拒绝生成、已知种子交集和替代种子上的生成/冻结/篡改/来源审核流程。

```powershell
.\.venv\Scripts\python.exe -m pytest tests scripts/tests -q --tb=short --noconftest -p no:cacheprovider --basetemp runs/receiver_review_20261107
node --test tests/visual_pack_contract.test.mjs
pnpm --dir frontend check
```

代码提交 `732ef8f92d1e83c18f4df23f0afa444f49e30c8a` 的全库复跑为 **701 passed、1 skipped、1 warning**。本轮前端 77 项及构建、A 图件合同 4 项均通过。已从 GitHub 用全新克隆核对上述原 A/B 提交、4 份历史测试日志和 15 张 SVG 的哈希。[本次全库日志](../evidence/B/formal_v2_review_2026-11-07/final.log) · [前端日志](../evidence/B/formal_v2_review_2026-11-07/frontend.log) · [图件合同日志](../evidence/B/formal_v2_review_2026-11-07/figures.log)

## 新旧轨迹隔离

原 180 条轨迹全部退出正式评价。归档名为 `engineering_regression_v1`，原路径和原字节保留，旧首条用于工程测试的记录仍可复验。正式冻结和读取冻结包两条路径都会拒绝将旧候选标为 formal。

| 来源 | 种子范围 | 数量 |
|---|---|---:|
| R5 开发矩阵 | 10000–10179 | 180 |
| engineering_regression_v1 | 200000–200179 | 180 |
| A-N4b 来源 | 410000–410029 | 30 |
| B 本次预登记 formal_v2 | 600000–600179 | 180 |

新段由 B 从上述已登记区间外选择，沿用原 18 工况及工况内 10 轨迹的顺序。已登记的种子交集为 0。旧教师的 20 条 Observation 缺少完整场景种子，需要 A 核对来源组和训练划分。生成后工具将逐条核查实际内容哈希，覆盖旧矩阵、重建的 R5 场景、A-N4b 场景及旧教师初始公开观测投影。两阶段分别保留种子核查和生成后内容核查的结论。[隔离核查记录](../evidence/B/formal_v2_review_2026-11-07/review_index.json)

## 签核对象和运行命令

| 对象 | SHA256 |
|---|---|
| formal_v2 登记文件 | `ce91579098ea388d0a337c77d9ca6946569381cd24d3334c1303c67bf1373bdf` |
| 18 工况设计配置 | `2df33c1291b3aabeaa81dbe139e2740f54432cd7e4b629ea2d1bd67c1cbbd29c` |
| 配置 configs/learned_policy.json | `518c447945783600060ab6c404186f9dc2e78f107be317fa9b26b62a448fdee2` |
| 模型 a-n3-mlp-v1 的 weights.npz | `a5226264d3a60f7d858e4d410595668b44b8dbd4c9a8bfa05191c1fd80461e4a` |
| 统计规则 analysis_protocol.json | `649ecfc8c94c37f8118ae4996947df215ce6c7ed13a8e2ee55db267a5e0c1e1f` |

模型五文件 SHA、统计脚本所在的代码哈希、来源路径及 SHA 均在[生成前签核对象](../evidence/B/formal_v2_review_2026-11-07/generation/subject.json)。该目录的 A/B/C 回执是 pending 模板。先将 generation 复制到 `runs/v2_generation_review`，运行下列第一条命令独立复算 subject，各角色实际审核后在自己的副本填写 reviewer、notes 和 accepted。生成命令会检查三份回执和当前对象的一致性。

```powershell
.\.venv\Scripts\python.exe -m backend.formal_v2 --subject
.\.venv\Scripts\python.exe -m backend.formal_v2 --receipts runs/v2_generation_review --output runs/formal_v2_inputs
.\.venv\Scripts\python.exe -m backend.formal_v2 --verify runs/formal_v2_inputs/manifest.json
.\.venv\Scripts\python.exe -m scripts.prepare_formal_v2_review --candidate runs/formal_v2_inputs/manifest.json --output runs/v2_input_review
```

生成后 A 复核来源/训练划分和实际交集，C 复核 180 条清单、三策略共享输入及 SHA，B 复核运行与统计参数。将实际审查结论写入 leakage.json，经确认后设为 accepted 并计算 SHA256。各角色填写输入回执的 reviewer、reviewed_at、notes、status 和 leakage_sha256。以下命令索引回执、生成最终冻结包并运行。每一步成功后再执行下一步。

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_formal_v2_review --index runs/v2_input_review
.\.venv\Scripts\python.exe -m backend.formal_freeze --candidate runs/formal_v2_inputs/manifest.json --review runs/v2_input_review/review.json --output runs/formal_v2_frozen
.\.venv\Scripts\python.exe -m backend.formal_freeze --verify runs/formal_v2_frozen/manifest.json
.\.venv\Scripts\python.exe -m backend.formal_experiments --manifest runs/formal_v2_frozen/manifest.json --output runs/formal_v2_batch --stage smoke
.\.venv\Scripts\python.exe -m backend.formal_experiments --manifest runs/formal_v2_frozen/manifest.json --output runs/formal_v2_batch --stage cell --resume
.\.venv\Scripts\python.exe -m backend.formal_experiments --manifest runs/formal_v2_frozen/manifest.json --output runs/formal_v2_batch --stage coverage --resume
.\.venv\Scripts\python.exe -m backend.formal_experiments --manifest runs/formal_v2_frozen/manifest.json --output runs/formal_v2_batch --stage full --resume
.\.venv\Scripts\python.exe -m experiments.analyze_formal --manifest runs/formal_v2_frozen/manifest.json --run-index runs/formal_v2_batch/run_index.jsonl --output runs/formal_v2_analysis
```

540 是 180 条轨迹 × EDF、Value、Learned 的唯一策略键数。对同一轨迹使用同一输入及带种子的共享随机信道。每个 Learned 结果同时参加两组配对。分段放量复用同一台账，保留首次失败，最多同配置重试一次，选首次成功完整结果。样本数、失败和缺失同时报告。

A 的 A-N4b 封存状态为 blocked_diagnostics_verified。A 的 AI 事实复核为 changes_requested，其报告与前端措辞修改交 C 跟进。claim-A1 与 X1/X2/X3 仍为 pending。换机验收保持未完成，现有证据覆盖本机干净环境。接收人对公开分支完成独立复验后再登记代码签收。
