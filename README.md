# 星地智调

> 2026-11-10 最新状态：formal_v2 的 180 条冻结输入、540 次策略运行已完成并封存，Learned 结果为负，结果发布签核仍按原流程门控。最终离线演示候选包通过本机全新环境验收；30 条新开发轨迹、60 个状态通过重算，训练仍禁用。详见 [B 本轮交付报告](docs/team/B_交付报告_演示与开发试点_2026-11-10.md)、[演示操作与录屏交接](docs/handoffs/B_演示操作与录屏交接_2026-11-10.md)及[正式结果交接](docs/handoffs/B_delegated_formal_results_2026-11-10.md)。另一台物理电脑验收尚待实际执行。

本轮验证：后端全库 730 通过、1 项 Linux 专用跳过；前端 124 测试、TypeScript 与生产构建通过。learned 已接入 Runner/Guard 及五接口，异常 EDF 回退与 Windows 进程回收保留。原 WP2 集成历史见[WP2交接](docs/handoffs/B_WP2_learned_2026-11-04.md)。

当前候选以WP1统一版本为基础，已纳入A审计657f39c和C复核63c7740。A可按[B确认的教师支持域](docs/handoffs/B_teacher_support_2026-11-04.md)开展新版本小批生成与审计；此前进度见[B接续记录](docs/handoffs/B_next_readiness_2026-11-04.md)。原始分支与回执保留，共享main尚未更新。

## 当前能力与边界

- 规则链路：任务/窗口/能量 → EDF 或 value → Guard → 发送/接收/ACK/重传/去重 → 事件、指标和 ZIP。
- learned：可独立加载冻结权重并调用 `score_actions`；Runner/API 已支持 `edf`、`value`、`learned`，异常与结构全mask回退保持可追溯。
- 健康：正式适配器使用显式 synthetic 观测误差界；旧权重支持冻结 NPZ 离线推理。raw_fraction 不能作为 SOC、容量或在线原生 RUL。
- 前端：离线流程演示、历史规则矩阵、八项参数真实沙盒运行、共享 run_id、按策略事件回放、真实结果比较和 ZIP 导出；历史示例与真实来源分别标识。
- 旧矩阵为 180 轨迹×两规则共 360 次开发运行；formal_v2 为另行冻结的 180 轨迹×三策略共 540 次，Learned 加权按时交付率为 0，EDF 为 46.54%，Value 为 51.15%。成熟优化器与真实卫星验证尚未完成。

WP1集成顺序与历史验证见 [WP1 交接](docs/handoffs/B_WP1_integration_2026-11-03.md)。

## 环境与安装

Python 3.12；Node.js 20—24；pnpm 9—11。前端唯一锁文件为 `frontend/pnpm-lock.yaml`。后端依赖见 `requirements.lock.txt`，它不包含全部轮子来源和哈希；换机需独立验收。在仓库根目录执行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
pnpm --dir frontend install --frozen-lockfile
```

本机已有环境可直接使用；不要复制其他电脑绑定解释器的 `.venv`。

## 启动后端与前端

终端一，在仓库根目录启动：

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --workers 1
```

终端二，在仓库根目录启动：

```powershell
pnpm --dir frontend dev --host 127.0.0.1
```

按 Vite 输出地址打开页面。开发和预览服务器默认将 `/runs` 代理到 `http://127.0.0.1:8000`，无需跨域配置。页面“证据链”可输入已存在的 run_id，读取后端真实运行。未接入的页面内容保持 FIXTURE 标识。

API 文档：<http://127.0.0.1:8000/docs>。目前可通过 API 提交新规则运行；页面创建真实运行属于后续联调。接口详见 [H03](docs/handoffs/H03_api_2026-10-29.md)：

- `POST /runs`：提交规则或learned配置，返回 run_id；每请求一至两策略。
- `GET /runs/{id}`：状态和进度。
- `GET /runs/{id}/events?after=0&limit=500`：分页事件。
- `GET /runs/{id}/results`：仅完成后提供正式结果。
- `GET /runs/{id}/export`：仅完成后提供 ZIP。

页面刷新恢复 run_id，不应重复提交。failed/未完成运行不展示正式指标。

## 独立规则运行与模型检查

以下输出目录必须是新的或空的：

```powershell
.\.venv\Scripts\python.exe -m backend.cli policy-run --config configs/scenarios/r3_multiblock.json --policy edf --output runs/example_edf
.\.venv\Scripts\python.exe -m backend.cli policy-run --config configs/scenarios/r3_multiblock.json --policy value --output runs/example_value
.\.venv\Scripts\python.exe -m backend.cli policy-run --config configs/scenarios/r3_multiblock.json --policy learned --output runs/example_learned
```

learned也可将下列policy-run命令的`--policy edf`改为`--policy learned`独立运行；模型权重由服务端冻结配置提供。模型校验包含在下文使用工作区临时目录的全库验证中。模型五文件在 `artifacts/models/a_n3_policy_v1/`，运行配置为 `configs/learned_policy.json`。权重和归一化 SHA 必须与配置及 manifest 一致；不要以重新训练替代恢复冻结模型。模型包、训练数据与模型卡均随候选版本保存。加载和评分成功不代表调度效果成立。

## 旧资产恢复

旧资产保持只读，按以下相对布局放置：

```text
<项目父目录>/
  starlink-ai6g/
  交付包/星地智调_团队研发包_2026-10-26_v3/
    PACKAGE_MANIFEST.csv
    assets/legacy_battery/
```

`configs/legacy_assets.json` 的 `legacy_root` 指向上述兄弟目录。恢复整个 v3 包及其清单，核对包内来源/哈希；这些旧资产不随代码仓库发布。其他机器从团队冻结研发包恢复相同文件，不依赖作者绝对 D 盘路径。若调整本机路径，请保留来源、哈希及变更记录，不修改旧资产内容。A 原分支内部“交付包”布局在本候选中已按 B 的现有布局解决，详见 WP1 交接。

## 验证

全库测试需要先恢复旧资产。PowerShell 中创建工作区临时目录，避开系统 Temp 权限问题：

```powershell
$reviewRoot = Join-Path 'runs' ('verify_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $reviewRoot | Out-Null
.\.venv\Scripts\python.exe -m pytest tests -q --tb=short --noconftest -p no:cacheprovider --basetemp "$reviewRoot/pytest" --junitxml "$reviewRoot/tests.xml"
pnpm --dir frontend check
```

测试、构建、真实 HTTP 和浏览器视觉验收分别记录，不能相互替代。WP1证据见 [集成验证目录](docs/evidence/B/WP1_integration_2026-11-03/README.md)。

## 协作与后续工作

[协作规则](CONTRIBUTING.md)、[公共合同](docs/contracts/README.md)、[任务板](docs/task_board.csv)、[优化方案](docs/superpowers/plans/2026-11-02-project-optimization.md)。B 下一项为接收人复验及正式实验冻结；A 推进数据与标签有效性；C 推进真实请求和页面联调。合同变更按三方确认规则执行。

旧日期记录保留在 [本轮集成前 README](docs/history/README_before_WP1_2026-11-03.md)，当前能力以本文件与最新交接为准。
