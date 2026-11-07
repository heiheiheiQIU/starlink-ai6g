# B 冲刺首轮工程交接

状态：`ready_for_review`。本轮已接收 A/C 最新交付，完成冻结层、三策略运行台账和配对统计工程；正式冻结与收益结论仍待实际独立签核。

## 交付范围

- A/C 集成提交：`1a51ae91fc380e5e71dbf4d8f4fbaf93526f9ee7`。B 功能初始提交 `9d89ce4c907b12b13385e76198615c9e94f31a1d`；其后修复提交请用 `git log -1 --format=%H -- backend/formal_freeze.py backend/formal_experiments.py` 解析。最终目录文件哈希见证据清单。
- `backend/formal_freeze.py`：保留候选原字节，另封装模型、配置、统计、三方回执与来源证据；冻结和运行均重新核哈希。
- `backend/formal_experiments.py`：三策略、追加式尝试台账、一次失败重试、首次成功选择、进程中断恢复；运行的完整配置/策略运行参数必须与冻结配置一致。
- `experiments/analyze_formal.py`：两个主比较、18 格等权、格内配对 bootstrap 10000 次；缺失不补零、重试不增加独立样本。`statistical_verdict` 供审核，`formal_verdict` 在结果签核前保持未完成。
- `requirements-materials.lock.txt`：报告测试用的可选依赖。本机补装 python-docx 1.2.0、lxml 6.1.3 后原报告测试可运行；不改变后端核心依赖。

## 运行和接收步骤

在仓库根目录、Python 3.12 环境：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-materials.lock.txt
.\.venv\Scripts\python.exe -m pytest tests/test_formal_freeze.py tests/test_formal_experiments.py tests/test_formal_analysis.py -q
.\.venv\Scripts\python.exe -m backend.formal_freeze --help
.\.venv\Scripts\python.exe -m backend.formal_experiments --help
.\.venv\Scripts\python.exe -m experiments.analyze_formal --help
```

生产冻结之前，先准备 leakage.json：标明候选/模型 SHA、来源文件相对路径及逐字节 SHA、统一编码与来源映射方法、排除种子和内容、实际碰撞审核结论。来源文件必须可读并随冻结包保存。`freeze_binding(candidate, model_config, analysis_protocol)` 给出代码、模型、配置和统计对象；A/B/C 各自回执必须同时接受该 binding 与 **leakage_sha256**。三份回执的 reviewer 不同，scope 为 formal，状态 accepted 或 accepted_with_notes。具体字段见测试 fixture；fixture 回执不能用于生产。

review.json 引用三份回执与来源审查的路径、SHA；不要代填成员签名。先由三人判断下列 holdout 暴露问题，再冻结。

```powershell
.\.venv\Scripts\python.exe -m backend.formal_freeze --candidate <候选目录>/manifest.json --review <审核目录>/review.json --output <新冻结目录>
.\.venv\Scripts\python.exe -m backend.formal_experiments --manifest <冻结目录>/manifest.json --output <新批次目录> --stage smoke
.\.venv\Scripts\python.exe -m backend.formal_experiments --manifest <冻结目录>/manifest.json --output <批次目录> --stage cell --resume
.\.venv\Scripts\python.exe -m backend.formal_experiments --manifest <冻结目录>/manifest.json --output <批次目录> --stage coverage --resume
.\.venv\Scripts\python.exe -m backend.formal_experiments --manifest <冻结目录>/manifest.json --output <批次目录> --stage full --resume
.\.venv\Scripts\python.exe -m experiments.analyze_formal --manifest <冻结目录>/manifest.json --run-index <批次目录>/run_index.jsonl --output <新统计目录>
```

代码或证据变更后须重新审核，不能把旧回执直接套到新 binding。结果转正式 claim 仍需要 A 独立复算、C 材料口径核对、B 原始运行复核和对应结果包 SHA 回执；当前入口不会自动提升为正式发布。

## 本轮证据及已知限制

- A-N4b 审计 `--verify` 退出 0；仅接受阻塞诊断完整性，训练关闭。旧模型五文件保留。
- 来源初查未发现候选与 A-N4b 的 Scenario 内容碰撞、或旧 20 源初态 Observation 投影碰撞；旧源缺完整场景/seed，不能据此宣称全量来源审核通过。记录为 B_checked_pending_A_C_review。
- **holdout 暴露：** 工程测试在生产冻结前使用了 `formal_v1_cell_00_trace_00`，审查探针还跑了该轨迹的缩短时域 EDF。没有根据结果调模型/seed/工况/统计；但不能再声称 180 条完全未见。A/C 应判断保留并披露，或另立独立 holdout 版本；若换版本，需先升级输入协议与测试，禁止静默改种子。
- 三个真实开发事件包已保存：手动 ACK 丢失脚本；损坏 NPZ 导致 EDF 回退；注入高分探针被能量约束拒绝。后者不是训练模型行为，坏包案例使用隔离开发回调，不进入正式受信注册表。
- 三策略开发正常场景耗时约 EDF 0.107s、Value 0.095s、Learned 0.534s，不能直接作为全矩阵耗时承诺；端到端时延与纯前向分开。
- 图件复核发现 B-F01/B-F02/C-F02/C-F03 需修改；见 B 图件回执。没有代改 C 的生成源/预览或代签 accepted。
- 未完成：A/C 来源与冻结签核、正式 540 次运行、正式结果签核、真实浏览器黄金链终验、另一台机器换机、最终报告/PPT/视频/上传。当前仅本机工程测试和开发证据。

实际测试命令、退出码、通过数、文件 SHA、原始事件和开发来源审核保存在 `docs/evidence/B/sprint_2026-11-07/`。接收人先核清单哈希，再执行上述定向测试；返回 accepted / accepted_with_notes / changes_requested / blocked，并注明复验范围。

最终本机验证：697 passed、1 Linux 跳过、1 既有 AnyIO 弃用警告；前端 77 项与 TypeScript/Vite 构建通过；修复后定向 38 项通过。证据文件 SHA256SUMS.json 共登记 39 个文件。
