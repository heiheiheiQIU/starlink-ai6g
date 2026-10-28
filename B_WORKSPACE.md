# B工作区入口

更新：2026-10-28。角色：通信仿真、公共合同、后端与集成。

## 从哪里开始

1. 阅读[我的工作路线](docs/superpowers/plans/2026-10-28-b-work-roadmap.md)。R0已取得环境/推理/测试证据，状态为ready_for_review；主仓库默认资产配置适配待A复核。下一项为R1/H00公共合同。
2. 开发目录是本文件所在的 `starlink-ai6g`；使用 `feature/simulator`，通过PR交接到main。
3. 开工先执行 `git status --short --branch`，确认分支、已有修改及队友交接。不要用reset/clean删除看不懂的修改。
4. 任务做到 `ready_for_review` 后交给对应成员；只有接收人能标记 `accepted`。

## 本机目录

| 位置 | 用途 |
|---|---|
| `D:\人工智能挑战赛\starlink-ai6g` | 唯一产品开发目录；A已有代码继续保留 |
| `D:\人工智能挑战赛\星地智调_团队研发包_2026-10-26_v3` | 方案和只读旧成果参考；不是开发目录 |
| `.venv/` | 本工作区独立Python环境，不提交Git |
| `configs/legacy_assets.local.json` | 本机资产路径配置，不提交Git；只改路径，不改资产 |
| `runs/` | 本机验证日志与临时运行结果，不提交Git |
| `experiments/runs/<run_id>/` | 后续正式实验原始产物，不提交Git；交接须另附清单/哈希 |

本文件含本机路径，是内部开发资料，不放进匿名参赛材料。

## 文件归属速查

- B编辑：`backend/contracts.py`、`backend/simulator/`、`backend/policies/{edf,value,teacher,guard}.py`、`backend/api/`、`backend/{cli,evaluation}.py`、对应测试、公共配置及合同、`experiments/`、`docs/contributions/B/`。
- A编辑：`backend/health/`、`backend/policies/learned.py`、`training/`及其测试。B负责复核和接口接入，跨目录修改先登记。
- C编辑：`frontend/`、报告/PPT/视频整合；B提供技术原稿与原始结果。
- `docs/evidence/A1/`是已有历史证据，不覆盖为本机验证结果。
- 合同变更由B维护，A/C共同确认；不得复制出第二套同名公共类型。

## 环境使用

独立venv已安装并实际验证：Python 3.12.14、NumPy 2.1.3、PyTorch运行时2.5.1+cpu（发行包版本2.5.1）、pytest 8.3.5；pip check通过。系统 `py` 启动器未发现已安装Python，因此直接使用venv解释器，无需激活脚本：

```powershell
Set-Location 'D:\人工智能挑战赛\starlink-ai6g'
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip --version
```

实际依赖快照、安装来源及wheel哈希见[环境证据](docs/evidence/B/R0_2026-10-28/README.md)。当前 `requirements.lock.txt` 只固定三个直接依赖，不能叫完整依赖锁；新增freeze是本次Windows环境快照，也不是跨平台离线安装包。venv的基础解释器来自Codex缓存，不能将整个venv复制给队友；换机应重新创建环境。

旧资产默认配置保留了队友的目录结构。本机另有 `configs/legacy_assets.local.json`，供接受 `--config` 的命令显式使用。**现有部分测试硬编码默认配置，因此本机配置不会自动修复全部旧测试。** 解决方式必须登记并由A复核，不能通过改legacy或伪造路径来掩盖。

A1审计已通过以下入口实际执行，7项资产哈希一致，LSTM/BiLSTM各两个窗口真实前向完成。输出与历史证据隔离，不是新通信实验结果：

```powershell
.\.venv\Scripts\python.exe -m training.inspect_legacy --config configs/legacy_assets.local.json --output-root runs/a1_local_review
```

测试结果必须区分：主仓库使用工作区临时目录时为36通过、5失败、20错误，未通过项均是默认资产路径不存在；同一提交的隔离验证快照仅替换资产配置后61项通过。后者不能称为主仓库默认命令通过。最初默认临时目录还遇到权限错误；后续测试使用工作区内新的专用 `--basetemp` 目录，避免删除或复用有价值的目录。

详见[R0报告及复现步骤](docs/evidence/B/R0_2026-10-28/README.md)与[交A复核单](docs/handoffs/R0_environment_2026-10-28.md)。尚未代A签收，也未改动A代码、测试或团队默认配置。

## 每天结束

记录产物路径、验证命令和日志、失败/未验证项、下一项任务；更新自己的任务状态。提交只包含本次相关源文件，禁止提交venv、权重、数据和运行产物。接口交接写入 `docs/handoffs/`，验收回执由接收人写入 `docs/acceptance/`。

本次工作区准备只新增入口、路线和本机配置，并切换角色分支；没有实现H00、仿真、API或新实验，也没有代替A/C签收。
