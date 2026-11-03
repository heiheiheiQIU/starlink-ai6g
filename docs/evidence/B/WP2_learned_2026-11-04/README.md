# WP2 learned集成与故障验证

2026-11-04；synthetic开发验证，不是正式AI效果实验。实现范围和失败语义见[B交接](../../../handoffs/B_WP2_learned_2026-11-04.md)。

## 实际检查

测试与运行来源SHA、最终JUnit统计、HTTP比较摘要见verification.json。原始失败/成功报告均保留，不删除初次红色记录。initial_full.xml是审查前543通过的历史版本；release.xml为修复后的最终版本，不能混用。

- 完整候选：缺失/重复/未知任务/NaN回退，正常idle、空队列与结构全mask分别检查。
- 进程：正常推理、评分卡死、推理退出、运行worker退出、run超时、close、父服务强杀、Job登记前的两种父死窗口。
- 文件故障：持续状态读锁不终止监控，后续run仍超时回收；ZIP拒绝坏产物和坏manifest。
- 身份：冻结manifest受信任SHA、五文件一致性、验证配置快照；重传时保留原模型评分；单模型和混合模型hash符合合同。
- Windows真实uvicorn与Vite生产预览代理：新建运行、状态、两条/页事件、结果、ZIP全部通过，配对输入哈希一致。4次policy-run中EDF重复一次，独立策略共三种。
- 前端完整测试、TypeScript与Vite构建通过；没有浏览器视觉或第三台机器验收。

Windows本机只跳过Linux专属僵尸进程回归；源码已判别Linux Z/X状态，但没有Linux实测环境。既有AnyIO弃用警告保留。

## 复跑

在仓库根恢复旧资产与锁定环境后，用新目录执行：

```powershell
$reviewRoot = Join-Path 'runs' ('wp2_repeat_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $reviewRoot | Out-Null
.\.venv\Scripts\python.exe -m pytest tests -q --tb=short --noconftest -p no:cacheprovider --basetemp "$reviewRoot/pytest" --junitxml "$reviewRoot/tests.xml"
pnpm --dir frontend check
.\.venv\Scripts\python.exe docs/evidence/B/WP2_learned_2026-11-04/verify_http.py --output "$reviewRoot/http"
```

HTTP脚本需8000、4179端口空闲，创建独立运行根并保存ZIP；Windows上将自己启动的服务加入Job，异常时也关闭进程树。run_id和壁钟耗时随复跑变化，科学输入及配置对齐按哈希判断。脚本不训练、不生成新训练样本，HTTP日志和XML含内部路径，不作匿名作品附件。

旧WP1验证脚本固定于当时“learned尚未开放”的版本；回放历史证据应检出其固定SHA，新版本使用本目录脚本。
