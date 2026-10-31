# B1 审计修复与后续执行进度

状态：ready_for_review。本次为本地修复及准备交付，尚未取得相邻签收。

基线：`d68d3cb`，分支 `feature/shared-channel-r5`。测试在该基线加当前未提交差异上执行，不能把结果写作基线提交本身的测试结果。

## 修复与验证

- 历史 seed 入口 `docs/evidence/B/seed_P2_2026-10-30/smoke.py` 原字节保留；可执行修订入口为 `scripts/verify_seed_p2.py`。
- 修订入口依据 `pyproject.toml` 和 `backend/api/main.py` 定位项目根，输出递归创建目录，支持干净副本和外部工作目录启动。
- 新测试复制所需源码到没有 runs 的干净副本，在项目目录及外部目录各运行两次；实际启动 TestClient 和工作进程，核对 seed、ZIP、产物哈希及请求未修改。
- 根目录修复前 2 failed（ModuleNotFoundError）；仅修根目录后 2 failed（FileNotFoundError）；目录修复后 2 passed。两类失败分别保存 XML。
- 最终全库 309 passed，1 条既有 Starlette/AnyIO 弃用警告；证据为 `docs/evidence/B/audit_followup_2026-10-30/final.xml`。
- 首次裸 pytest 为 236 passed、71 setup errors，原因是默认临时目录权限；改用工作区 basetemp 后，修复前基线为 307 passed。未把环境错误当作业务回归。

复现（在项目根执行；basetemp 使用新的专用空目录，避免覆盖历史证据）：

```powershell
.\.venv\Scripts\python.exe scripts/verify_seed_p2.py
.\.venv\Scripts\python.exe -m pytest tests/test_seed_reproduction.py -q -p no:cacheprovider --basetemp runs/receiver_seed_tmp_01
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp runs/receiver_full_tmp_01
```

入口结果位于 `runs/seed_p2_reproduction/actual/verification.json`，与旧证据输出目录分开；重复运行创建新的运行目录，verification.json 更新为最近一次结果。它仍是 TestClient 验证，不是外部网络或浏览器端到端验证。

## 任务板修复依据

- B-R0、B-R2 从 `3329284` 查回；B-R0 的 A 回执位于本地 `origin/feature/ai:docs/acceptance/R0_A_2026-10-28.md`，其 accepted_with_notes 仅限环境和冻结资产范围。
- R0 证据七文件从 `70c5064` 恢复并与 Git blob 逐字节核对。归档恢复时发现 requirements.freeze.txt 自动转换为 CRLF，已从原 blob 恢复 LF，并为证据设置字节保留属性。文件内个人路径为历史内部记录，不能直接用于匿名参赛材料。
- B-R2 保持 ready_for_review，明确等待 `d4716bf` 四项手算独立签收范围确认；B-R3 保留现有较新回执状态。
- A-N1 已是正式 synthetic 适配器有限签收，保持不变。A-N2 移除已经过时的 H01 阻塞说明；A-N3 移除“教师接口尚未交付”的旧描述，保留最新数据和模型阶段待核实状态，不推断远端事实。

## B2 当前阻塞

指定候选 `866df43` 在本地无法解析。普通及提升权限的 `git fetch origin --prune` 均连接 GitHub 443 失败，提升权限也未解决网络连接；不是自动审批拒绝。本地旧 `origin/feature/ai` 不含指定教师数据交付，不能用旧引用代替目标版本验收。

状态为 awaiting_source，尚未重算 A 的20标签、验收12/4/4或出具 A-N3 accepted 回执。网络恢复后先取得完整候选 SHA 和 handoff，按既定清单完成全量复算；不要求 A 重新训练来绕过版本缺失。

## B3 已完成的独立准备

当前 B 教师接口及模型支持边界已核查；重新运行原有20初始状态预检为20 OPTIMAL、0超时、CPU 0.125s，原始结果在 `runs/b_next_20261030/teacher_timing/`。这是简单初始状态计时，不足以预测高密度场景成本，也不是 A 数据验收或扩样完成。

扩样和接口建议见 `B_training_scale_interface_2026-10-30.md`，待 A 固定候选到达后对齐，避免平行实现与其样本格式冲突。

## 执行裁定与后续

- 复用当前专用 B 分支，隔离副本用于复跑；不另建 worktree。成本：工作差异需保持清楚，不能与其他同时修改混淆。
- 历史证据脚本保持原字节，新入口独立交付，替代直接修改证据脚本。成本：接收人须按本交接使用新入口。
- A 固定数据/特征尚未取得，因此暂不冻结新批量格式或训练数据；先完成现有接口核查及扩样提案。成本：规模化生成仍待对齐，未宣称 B3 完成。

后续依次为 B2 数据独立主验、A/B 接口对齐及代表场景计时、规模化生成。B4 正式模型接入、B5 AI实验、B6 实际集成仍依赖交付和回执；本次未合并 main。

## 网络重试后的状态更新

随后按用户要求使用计算机网络重试成功，已获取 `866df43d124e62a77081a7acd2e095c98b34c172`。旧awaiting_source状态仅描述前一轮现场，不再是当前阻塞。B2独立主验及复核发现5组相同观测跨集合，回执为changes_requested，详见 `docs/acceptance/A_N3_data_B_2026-10-30.md`。B1 verification.json的文件哈希是上一轮结束时的快照，后续任务板及本交接更新不回填该历史快照。
