# 星地智调产品集成目录

2026-10-29 R3：B已增加显式启用的确定性接收/ACK/超时重传/去重环境、事件评价器和单策略运行导出；使用synthetic健康输入与manual动作脚本。可独立复跑，不依赖A模型或C页面。实现与验收范围见[R3交接](docs/handoffs/B_R3_protocol_2026-10-29.md)；尚未签收时不视为B-N2整体完成。

```powershell
.\.venv\Scripts\python.exe -m backend.cli run --config configs/scenarios/r3_ack_loss.json --output runs/my_r3_ack_loss
```

输出目录必须新建或为空。四个`r3_*.json`是可执行合成场景；`minimal.json`仍用于R2发送验证。完成的运行包含config、manifest、status、events、results、execution.log及能量账本。完整运行状态不表示所有任务成功；基线、统一guard、教师和API仍属后续任务。

2026-10-29 B-N2/R2首轮：已实现单策略、确定性合成场景的任务/窗口/能量/发送环境；接收与ACK尚在后续R3。运行与四项手算验收见[R2交接](docs/handoffs/B_N2_R2_2026-10-29.md)。日志由真实执行生成，不能作为卫星实测或策略收益结果。

2026-10-29 H00干净集成：合同修订c54c79d已获A/C对同一提交的accepted。本次仅纳入合同、Schema、测试、证据与回执，进入main后作为v1.0冻结基线；未捆绑C设计或A内部健康核心。详见[冻结与范围记录](docs/contracts/FREEZE_2026-10-29.md)。仿真/API仍待B-N2后续实现。

更新：2026-10-27。此目录是本工作区接收成员成果后的开发入口。当前仅集成成员A的A1旧资产审计/离线前向模块，不是完整通信产品。

团队先读：[协作规则](CONTRIBUTING.md)、[公共接口合同](docs/contracts/README.md)、[下一阶段任务](docs/team/NEXT_TASKS_2026-10-27.md)和[任务板](docs/task_board.csv)。三人只在本仓库协作，不再通过反复制作ZIP同步日常代码。

远程私有仓库：<https://github.com/heiheiheiQIU/starlink-ai6g>。成员获得访问权限后执行：

```powershell
git clone https://github.com/heiheiheiQIU/starlink-ai6g.git
cd starlink-ai6g
git switch feature/ai          # A
git switch feature/simulator   # B（在自己的克隆目录执行）
git switch feature/frontend    # C（在自己的克隆目录执行）
```

不要三人共用同一个本地目录；每人独立克隆，只向自己的角色分支提交，再通过Pull Request合入`main`。

## 当前验收状态

- A1离线资产审计和严格权重推理：accepted_with_notes；本机原47项测试通过，增加14项边界测试并修复后61项通过。
- H01正式HealthEstimate交接：未通过完整验收；当前返回内部LegacyPrediction，无estimate_health(history, now_s)。需B的H00合同和A2适配。
- A2健康估计、A3通信评分器、A4消融与技术供稿：未交付。
- B仿真：R2发送验证与R3合成协议/评价已实现，待接收人验收；统一guard、基线、教师和API尚待后续。C前端尚未集成到本分支。

原始交付保留在工作区`星地智调/`。不要在原件继续开发；后续A/B/C在此目录按各自所有权协作。

## 输入与环境

`configs/legacy_assets.json`已适配本工作区，指向`../交付包/星地智调_团队研发包_2026-10-26_v3/assets/legacy_battery`。使用v3是为了保持A原始审计的资产基准，不表示v3是最新团队说明。不要移动或改写冻结资产。

推荐独立环境（需机器安装Python 3.12；安装依赖需要网络/本地轮子）：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pytest tests -q --noconftest -p no:cacheprovider
.\.venv\Scripts\python.exe -m training.inspect_legacy --config configs/legacy_assets.json --output-root runs/a1_review
```

以上独立安装流程是推荐操作，本轮没有执行联网安装。`requirements.lock.txt`只固定三个直接依赖，没有锁住全部传递依赖、轮子来源和哈希，不能宣称完整环境锁。

本轮实际验证使用本机Python 3.12.14解释器，借用原交付`.venv/Lib/site-packages`中的NumPy 2.1.3、PyTorch 2.5.1+cpu、pytest 8.3.5；没有启动失效的队友venv解释器。复现本轮验证可在本目录PowerShell运行：

```powershell
$pythonExe = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$env:PYTHONPATH = (Resolve-Path '../星地智调/.venv/Lib/site-packages').Path
$env:PYTHONIOENCODING = 'utf-8'
& $pythonExe -m pytest tests -q --tb=short --noconftest -p no:cacheprovider
& $pythonExe -m training.inspect_legacy --config configs/legacy_assets.json --output-root runs/a1_review
Remove-Item Env:PYTHONPATH
```

这种借用方式依赖当前交付文件的Python版本及二进制包兼容性，不作为最终换机安装验收。B接管后建立干净环境并补完整依赖记录。

## 文件归属与证据

- `backend/health/legacy_adapter.py`：离线冻结NPZ推理，不是在线健康接口。
- `backend/health/legacy_models.py`：与旧权重对应的LSTM/BiLSTM架构。
- `training/legacy_audit.py`、`training/inspect_legacy.py`：资产/标签审计及证据生成。
- `tests/`：原测试与集成审查补充回归。
- `docs/evidence/A1/`：A交付的历史证据原样保留。
- 新审查日志及重新生成的证据在工作区`审查输出/成员A验收_2026-10-27/`，不要混淆作者原日志与本机重跑日志。
- 审查结论见`../审查输出/成员A验收_2026-10-27/审查与合并报告.md`。

原目录的`.git`指向队友电脑worktree，原`.venv`绑定队友解释器；两者均未复制。本站已为集成目录重新初始化独立Git仓库，并建立`main`、`feature/ai`、`feature/simulator`、`feature/frontend`；当前提交以`git rev-parse HEAD`为准。这不是恢复队友提交历史。远程`origin`为上述私有仓库，协作与合并以远程分支和Pull Request记录为准。

禁止把raw_fraction直接当SOC、容量、能量或在线原生RUL；允许预测大于1，不私自裁剪。旧CSV标签吻合只能证明标签对应，不证明全部X、标准化器和原始数据谱系已经重建。
