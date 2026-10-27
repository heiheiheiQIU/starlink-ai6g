# 星地智调产品集成目录

更新：2026-10-27。此目录是本工作区接收成员成果后的开发入口。当前仅集成成员A的A1旧资产审计/离线前向模块，不是完整通信产品。

## 当前验收状态

- A1离线资产审计和严格权重推理：accepted_with_notes；本机原47项测试通过，增加14项边界测试并修复后61项通过。
- H01正式HealthEstimate交接：未通过完整验收；当前返回内部LegacyPrediction，无estimate_health(history, now_s)。需B的H00合同和A2适配。
- A2健康估计、A3通信评分器、A4消融与技术供稿：未交付。
- B仿真/API、C前端：当前目录未实现。

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

原目录的`.git`指向队友电脑worktree，原`.venv`绑定队友解释器；两者均未复制。本站已为集成目录重新初始化独立Git仓库，并建立`main`、`feature/ai`、`feature/simulator`、`feature/frontend`；当前提交以`git rev-parse HEAD`为准。这不是恢复队友提交历史，当前也没有远程推送。

禁止把raw_fraction直接当SOC、容量、能量或在线原生RUL；允许预测大于1，不私自裁剪。旧CSV标签吻合只能证明标签对应，不证明全部X、标准化器和原始数据谱系已经重建。
