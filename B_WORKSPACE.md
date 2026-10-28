# B工作区入口

更新：2026-10-28。角色：通信仿真、公共合同、后端与集成。

## 从哪里开始

1. 阅读[我的工作路线](docs/superpowers/plans/2026-10-28-b-work-roadmap.md)。当前下一项是R0环境基线检查，然后R1/H00公共合同。
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

已创建基于Python 3.12.14的独立venv；尚未安装项目依赖或验证旧模型。系统 `py` 启动器未发现已安装Python，因此当前直接使用venv解释器，无需激活脚本：

```powershell
Set-Location 'D:\人工智能挑战赛\starlink-ai6g'
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip --version
```

后续R0执行依赖安装与版本记录。当前 `requirements.lock.txt` 只固定三个直接依赖，不能叫完整依赖锁。venv的基础解释器来自Codex缓存，不能将整个venv复制给队友；换机应重新创建环境。

旧资产默认配置保留了队友的目录结构。本机另有 `configs/legacy_assets.local.json`，供接受 `--config` 的命令显式使用。**现有部分测试硬编码默认配置，因此本机配置不会自动修复全部旧测试。** 解决方式必须登记并由A复核，不能通过改legacy或伪造路径来掩盖。

依赖和资产检查完成后，A1审计可使用以下入口；目前未执行，输出与历史证据隔离：

```powershell
.\.venv\Scripts\python.exe -m training.inspect_legacy --config configs/legacy_assets.local.json --output-root runs/a1_local_review
```

## 每天结束

记录产物路径、验证命令和日志、失败/未验证项、下一项任务；更新自己的任务状态。提交只包含本次相关源文件，禁止提交venv、权重、数据和运行产物。接口交接写入 `docs/handoffs/`，验收回执由接收人写入 `docs/acceptance/`。

本次工作区准备只新增入口、路线和本机配置，并切换角色分支；没有实现H00、仿真、API或新实验，也没有代替A/C签收。
