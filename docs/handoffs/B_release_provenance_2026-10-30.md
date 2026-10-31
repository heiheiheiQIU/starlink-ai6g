# B：发行副本版本来源修复

状态 ready_for_review。源提交 `921a24b`。本轮继续集成前复跑时发现：不含.git的发行副本如果嵌套在另一个Git仓库，`git rev-parse HEAD`会找到外层仓库，把外层提交误记为当前源码版本。CLI与教师预跑均可复现；两项新增真实子进程测试先失败，记录的错误版本为外层1343cbf。

修复在读取HEAD前要求项目根存在.git元数据；支持普通仓库的目录及worktree的.git文件。无本地元数据时，CLI沿用显式config.code_revision或源码哈希回退，教师沿用源码哈希回退；git程序缺失与命令失败路径保持兼容。没有修改冻结合同、仿真动作或指标。

验证：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_release_provenance.py tests/test_r3_feedback.py tests/test_teacher.py -q --noconftest -p no:cacheprovider --basetemp=runs/provenance_recheck --junitxml=runs/provenance_recheck.xml
```

实际定向24 passed，全库307 passed，保留现有1条Starlette/AnyIO弃用警告。测试构造一个有真实提交的外层仓库，再运行无.git副本，不依赖手工环境变量。固定源提交后另导出全新副本，在原仓库内直接跑CLI和教师20状态预跑，二者均正确记录unversioned-source-sha256，教师20 OPTIMAL/0超时。

证据 `docs/evidence/B/release_provenance_2026-10-30/`，包含RED/GREEN/全库XML、实际CLI及教师输出、哈希清单。审查时可把源提交归档后放进任何其他Git仓库内复跑，确保没有误认外层HEAD。

历史R3候选cac4b90未改写。其本轮复跑主动设置GIT_CEILING_DIRECTORIES到候选父目录，使用真实源码哈希回退；先前继承外层HEAD的两份尝试不作为有效版本证据。旧签收不会自动覆盖本轮新修复，新修复仍需相邻复核。
