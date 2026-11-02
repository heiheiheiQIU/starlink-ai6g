# B的R0环境、资产与测试基线

日期：2026-10-28（Asia/Hong_Kong）。被测源码提交：`9acbd6b`。状态：**ready_for_review，非accepted**。范围仅为工作路线第一步R0，未实现H00或通信产品。

## 结论

- 独立venv已安装固定直接依赖；Python 3.12.14、NumPy 2.1.3、PyTorch运行时2.5.1+cpu、pytest 8.3.5。pip check无冲突。
- 本机配置指向的7个资产逐一通过SOURCE_MANIFEST中的大小及SHA核验。
- 实际读取源/目标NPZ并严格加载LSTM与BiLSTM-Attention权重，各执行两个窗口前向；没有使用冻结预测JSON代替推理。
- **主仓库默认测试命令尚未全通过。** 根因包括本机临时目录权限和默认资产路径失配。指定工作区临时目录后，只剩路径问题。
- 同一提交的隔离源码快照，仅替换其中的资产配置后，**61项测试通过**。这证明了该环境及本机资产配置条件下的现有测试行为，不是主仓库默认配置已修复。
- 运行前后研发包148文件均通过完整性校验，`docs/evidence/A1/`原有文件哈希不变。backend、training、tests及团队默认资产配置未修改。

## 三次测试要分开看

| 执行条件 | 通过 | 失败 | 错误 | 退出码 |
|---|---:|---:|---:|---:|
| 主仓库默认配置、默认临时目录 | 4 | 5 | 52 | 1 |
| 主仓库默认配置、工作区临时目录 | 36 | 5 | 20 | 1 |
| 隔离快照、本机资产配置、工作区临时目录 | 61 | 0 | 0 | 0 |

第一组错误包括对 `C:\Users\yuzzz\AppData\Local\Temp\pytest-of-yuzzz` 的PermissionError。第二组全部失败/错误都源于默认路径 `../交付包/星地智调_团队研发包_2026-10-26_v3/assets/legacy_battery` 不存在；实际包位于仓库同级，没有“交付包”这一层。失败用例名称与错误信息完整记录在 [baseline-results.json](baseline-results.json)。

不为追求绿色结果修改A的测试、不删失败用例、不移动或软链接legacy目录、不修改主仓库默认配置。快照与原始跟踪文件逐一SHA比较，仅 `configs/legacy_assets.json` 不同；比较清单已记录在本机日志索引中。

## 本次实际推理观察

| 项目 | 实际结果 |
|---|---|
| 源NPZ | shape=(585,15,11)，20条run，cycle/cycles，stride=3 |
| 目标NPZ | shape=(79710,15,11)，100条run，orbit/orbits，stride=3 |
| 源LSTM原始归一化输出 | 0.8055816293、0.7995225787 |
| 目标BiLSTM原始归一化输出 | 1.1702452898、1.1421915293；未强行裁剪为[0,1] |
| 窗口起点/可用索引 | 起点0、3；可用14、17；now_index=13的首窗口被WINDOW_NOT_AVAILABLE拒绝 |
| 原生RUL | null，原因NATIVE_RUL_RESTORE_REQUIRES_FUTURE_RUN_MAX |
| 修正版源CSV标签对应 | 585/585完全一致，缺失0 |
| 原始源CSV标签对应 | 可比384中262一致，缺失201，最大绝对差65 |

以上只是冻结NPZ窗口上的模型前向及标签对照。没有证明新遥测预处理可用、目标数据谱系闭合、在线健康校准成立，也不能当作SOC、容量、能量、真实在轨RUL或本届通信收益。仅两种模型实际前向；第三个微调权重本次只核验文件哈希，未声称已前向验证。

## 证据文件

- [environment.json](environment.json)：实际解释器、CPU运行时及隔离状态。
- [requirements.freeze.txt](requirements.freeze.txt)：本次安装后的全部包版本快照。
- [installed-wheels.json](installed-wheels.json)：本次pip安装的16个发行包下载URL及SHA256；pip自身来自venv创建，未混称本次下载。
- [assets-audit.json](assets-audit.json)：实际资产哈希、NPZ结构、标签对照和模型输出。
- [baseline-results.json](baseline-results.json)：三次测试计数、失败用例和状态边界。
- [local-evidence-index.csv](local-evidence-index.csv)：本机原始日志、JUnit XML、推理样例、源码快照和配置的路径/大小/SHA。

大体积运行产物保存在被Git忽略的 `runs/workspace_baseline/` 与 `runs/a1_local_review/`，仅有本机路径不代表队友已收到；需要复核时按索引传递文件或在队友机器重跑。该目录是内部证据，含个人路径，不直接作为匿名参赛材料。

freeze仅是Windows CPython3.12环境快照，不是跨平台完整构建锁或离线轮子包。当前项目以源码运行，没有安装项目发行包，亦未验证pyproject中的构建流程或GPU推理。

## 复现命令

先在项目根目录运行。以下是当次实际采用的命令；再次运行请为日志及basetemp换一个新后缀，保留原证据。pytest会清理指定basetemp，禁止填已有业务目录。

```powershell
# 依赖安装（本次已执行）
.\.venv\Scripts\python.exe -m pip install --disable-pip-version-check --no-input --only-binary=:all: --index-url https://pypi.org/simple --report runs/workspace_baseline/pip-install-report.json -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip freeze --all

# 主仓库测试：仍预期因默认资产路径失败，原始输出已留存
.\.venv\Scripts\python.exe -m pytest tests -q --noconftest -p no:cacheprovider --basetemp=runs/workspace_baseline/pytest-tmp-r0-01 --junitxml=runs/workspace_baseline/pytest-workspace-temp.xml

# 本机配置的真实审计/推理：退出0
.\.venv\Scripts\python.exe -m training.inspect_legacy --config configs/legacy_assets.local.json --output-root runs/a1_local_review
```

本机配置由团队默认JSON复制，只将legacy_root改为 `../星地智调_团队研发包_2026-10-26_v3/assets/legacy_battery`，保存为UTF-8无BOM。该文件被忽略，不改变团队默认配置。

隔离快照的复现流程如下。运行时将 `validation_checkout` 换成尚不存在的新目录；当前留下的快照和日志仍可检查，不覆盖：

```powershell
$repo = (Get-Location).Path
$snapshot = Join-Path $repo 'runs/workspace_baseline/validation_checkout'
if (Test-Path -LiteralPath $snapshot) { throw 'Snapshot already exists; choose a fresh directory' }
$archive = "$snapshot.zip"
$snapshotTemp = "$snapshot-tmp"
$snapshotXml = "$snapshot-results.xml"
foreach ($p in @($archive, $snapshotTemp, $snapshotXml)) {
    if (Test-Path -LiteralPath $p) { throw 'Evidence destination exists; choose a fresh snapshot name' }
}
git archive --format=zip --output=$archive 9acbd6b
if ($LASTEXITCODE -ne 0) { throw 'git archive failed' }
Expand-Archive -LiteralPath $archive -DestinationPath $snapshot
$cfg = Get-Content -Raw -Encoding UTF8 configs/legacy_assets.local.json | ConvertFrom-Json
$cfg.legacy_root = [IO.Path]::GetFullPath((Join-Path $repo $cfg.legacy_root))
[IO.File]::WriteAllText((Join-Path $snapshot 'configs/legacy_assets.json'), ($cfg | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
Push-Location $snapshot
try {
    & (Join-Path $repo '.venv/Scripts/python.exe') -m pytest tests -q --noconftest -p no:cacheprovider --basetemp $snapshotTemp --junitxml $snapshotXml
} finally { Pop-Location }
```

审计入口自动生成的Markdown内部复现命令仍写死默认配置及输出点号；本次实际使用上面的显式local配置与runs目录，不能直接照抄该自动报告的命令覆盖历史证据。此文和索引记录真实执行条件。

## 待复核事项与下一步

R0接收人A应复查配置适配方式、关键模型输出和失败用例归因。建议后续为A的资产加载入口与测试增加显式配置选择，默认行为保持兼容；这是提案，当前没有修改A代码，也没有代A同意。

主仓库整套测试尚不能直接全绿，这一限制必须保留。它不阻碍B开始R1公共合同，但旧模型接入或发布验收前应解决。H00、正式HealthEstimate、学习评分器和通信环境仍为待实现/待交付，不能因R0通过部分检查提前验收。
