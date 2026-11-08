# B 交互仿真与正式评测交接 · 2026-11-09

交接状态为 ready_for_review。分支为 codex/b-sandbox-delivery-20261109，功能提交为 3bd22a30d864eb0bdd0a32b8efea426e1673b803，并发清理修复提交为 3f09926e78478c0ec235117d70fa605406977078。后端、前端和冻结模型均在该分支源码中。最新证据提交在功能提交之后。

## 本轮交付与状态

| 任务 | 实际交付 | 接收验收 |
|---|---|---|
| B0 | 原 formal_v2 subject、生成器、模型、统计脚本和仿真内核均沿用 48157a8；交互改动在独立分支。 | formal 后续在 48157a8 执行并重核三方绑定，正式冻结尚待第二阶段签核。 |
| B1 | 已取 A accepted 原件，B 独立核对 subject、模型和种子后出具本方 accepted。 | 缺 C 原始生成前回执，本轮候选生成待执行。A/B 原件和 SHA 见 evidence/B/sprint_2026-11-09/generation。 |
| B2 | 已有第二阶段模板生成工具 scripts/prepare_formal_v2_review.py。 | 待候选生成后 A/B/C 实签实际清单。 |
| B3/B4 | 五接口、八个场景轴加顶层 seed/策略、唯一确定性构造器、字段级 422、原始请求及编译配置 ZIP 证据均完成；旧完整配置请求兼容。 | C 按 docs/contracts/sandbox_scenario_edit_v1.md 接入。当前分支 frontend 与 C 最新 frontend 仅 README 有差异。 |
| B5 | 5 个两策略运行均实测 running 可读取第一策略已完成事件批次。每页 7 条排空，与 ZIP 完全一致，ID 连续。 | 事件按策略批次发布。C 按 policy_id 分流并按 sim_time_s 回放，完成态最后排空。单策略内实时流式显示仍需另行开发。 |
| B6 | S1/S2/S3、仅改健康档的对照、S3 同 seed 复跑共 5 个运行完成。 | A 复核 health_pair.json 和 S3 事件链；C 消费真实事件。所有数据为 synthetic/sandbox。 |
| B7/B8 | 既有正式运行、恢复、统计和冻结工具已回归。 | 等待 B1/B2 条件齐备后，在冻结提交实测正式预跑耗时，执行 540 个唯一策略运行及签核。正式结论仍为未完成。 |
| B9 | 新增真实自动策略 S3 ACK 重传案例和 S2 高分被能源 Guard 拒绝案例，复用并标记旧开发故障注入回退案例。 | cases 目录保留事件范围、输入身份和来源 SHA；正式图源数据待正式运行。 |
| B10 | 新 venv 离线安装 16 个依赖、pip check、无 Git 源码 5 个黄金运行、旧请求与模型缺失/损坏测试、完整离线 ZIP 逐成员哈希与解压启动通过。 | 同机 Windows x64/Python 3.12 验证。另一台物理机器与最终 C 页面交互验收待办。 |

## 真实场景结果

| 场景 | run_id | 事件数 | EDF 准时加权完成率 | Learned 准时加权完成率 |
|---|---|---:|---:|---:|
| S1 | sandbox_run_9809baca65f847d58fa961ccea9b635e | 103 | 1 | 0 |
| S2 | sandbox_run_245f69ffa2d54915a20b4574502dfd21 | 96 | 0 | 0 |
| S3 | sandbox_run_5bc5191b2e5048fab07986e850b6edae | 135 | 1 | 0 |

上表对应持久交接证据 http/verification.json 及同目录场景 results/events。离线包 golden_runs 与持久交接证据来自同一轮提交后运行。

S1 能源安全、链路可靠，EDF 完成全部任务。S2 接近储备线，临界健康下首批候选的 ENERGY_RESERVE 全部拒绝。保持其他轴与 seed 不变、仅改 healthy 后，同批检查全部通过，评分也发生变化。S3 含多块任务，EDF 出现 ACK_LOST_CHANNEL、ACK_TIMEOUT、同块重传及 DUPLICATE_BLOCK。冻结 Learned 在本组配置中选择 idle，按真实结果展示，策略优越性 claim 保持待定。

S3 重复运行的事件去除 run_id 和实测 latency_ms 后完全相同。运行耗时、ZIP 大小和关键原因计数见 verification.json；复现比较保留原始时延。不同健康输入的公开 Observation、初次 Learned 候选评分及 Guard 检查见 http/health_pair.json。

## 接收复验

1. 检出本分支，核对 docs/contracts/sandbox_scenario_edit_v1.json 及 configs/sandbox/S1.json、S2.json、S3.json。
2. 后端用 .venv/Scripts/python.exe -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --workers 1 启动。前端继续用既有 Vite /runs 代理。
3. 执行 .venv/Scripts/python.exe -m scripts.verify_sandbox --output 一个新目录，检查 5 个运行及 events/ZIP 对账。
4. A 对照 http/health_pair.json 和 cases/ack_retry.json、cases/guard_reject.json 签复 A2/A3；C 依据同一配置合同实现轴编辑和全局运行状态。
5. 正式输入生成前取得 C 原始 accepted，逐项比较 generation/subject，核对 SHA 后把三份回执提交到冻结版本的审查目录，再走原生成和第二阶段签核工具。

## 验证记录与离线包

- 后端相关回归 283 项通过，完整日志见 evidence/B/sprint_2026-11-09/regression.log。覆盖 API、Learned、协议、能量、合同、formal 候选/冻结/运行/统计等 18 个测试文件。全库测试曾在收集阶段长时间无输出，已停止，故只报告上述范围。
- frontend 的 pnpm test:run 共 77 项通过，pnpm build 通过。页面按钮及新版参数控件的浏览器验收归 C 联调。
- 源码包版本 3f09926，离线包路径为 runs/B_sandbox_offline_20261109.zip。包内包含源码、16 个 wheel、锁文件、前端构建产物、单端口启动器、5 个运行及 SHA256SUMS.json。
- 离线包 24,770,339 bytes，SHA256 为 36de40f1dac37b3d78bea0362314fc8e82b28aaa63c3f0e4b82ed02fc25b7a81。机器清单见 offline_package.json。解压后按 README.txt 操作，start.py 同时提供网页和 /runs 接口。
- 后续证据提交只增加文档和验证日志，离线源码包固定在上述已核验版本。包中现有前端仍需 C 加入新版轴控件，API 可直接使用三份请求 JSON。
- 审查发现的 seed 类型强转、sandbox 父目录链接越界已补回归测试；广泛回归发现直接清理与后台监督并发重入，已用同一重入锁串行化，复测通过。

后续优先级为 C 原始回执 → 180 候选 → 第二阶段三签 → 正式冻结与预跑 → 540 唯一运行与统计 → 结果三签。等待期间，A/C 可直接复核现有交互证据和新合同。
