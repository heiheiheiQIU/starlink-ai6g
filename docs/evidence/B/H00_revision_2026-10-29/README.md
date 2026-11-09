# H00审查修复验证证据

日期：2026-10-29（Asia/Hong_Kong）。角色B。实施基线`4cf2b7e`；被A/C审查的原候选提交`8497a3b`。状态`ready_for_review`，没有修复后的A/C accepted回执。

本次只修复公共合同校验及补充样例、文档，不实现仿真、教师求解或通信实验。三项要求来自`docs/acceptance/H00_A_2026-10-28.md`与`H00_C_2026-10-28.md`，均保留原件。

## 结果

- 新增42项审查回归：修复前36失败、6通过；失败原因为非法输入未被拒绝、缺少显式教师校验入口或Schema未拒绝空集合，未出现设置错误。
- 原75项加新增42项契约测试：117通过。原测试文件未修改。
- 主工作区全库：178通过、0失败、0错误；使用团队默认配置和本机恢复的真实旧资产。旧报告的25项路径失败不适用于本次已恢复布局，不改写历史报告。
- Schema重新导出逐字节一致；新增TeacherResult.candidate_scores的minItems=1。预测版本比较、候选键唯一/idle可行性、任务引用和缺测原因由Python校验。
- 修复后的交付文件SHA见delivery-files.csv；原2026-10-28清单仍对应旧Git提交，不适用于当前修改后的文件。
- 9个审查样例均标明非实验结果；六类场景仍是behavior_verified=false，未代替真实仿真行为测试。

## 实际命令

仓库根目录，先创建日志父级，再运行测试。重复验证须更换临时目录后缀，避免pytest清理已有有价值目录。

```powershell
New-Item -ItemType Directory -Force -Path runs/h00_revision_2026-10-29 | Out-Null
.\.venv\Scripts\python.exe -m pytest tests/test_h00_review_regressions.py -q --noconftest -p no:cacheprovider --basetemp=runs/h00_revision_2026-10-29/tmp-red --junitxml=runs/h00_revision_2026-10-29/red.xml
.\.venv\Scripts\python.exe -m pytest tests/test_contracts.py tests/test_h00_review_regressions.py -q --noconftest -p no:cacheprovider --basetemp=runs/h00_revision_2026-10-29/tmp-green --junitxml=runs/h00_revision_2026-10-29/contracts.xml
.\.venv\Scripts\python.exe -m pytest -q --noconftest -p no:cacheprovider --basetemp=runs/h00_revision_2026-10-29/tmp-full --junitxml=runs/h00_revision_2026-10-29/full.xml
.\.venv\Scripts\python.exe -m backend.contracts --schema-output runs/h00_revision_2026-10-29/schema-check.json
.\.venv\Scripts\python.exe -m pip check
```

RED命令是在仅新增测试、尚未修实现时执行的历史验证；当前修复代码运行此命令应全绿。具体测试XML计数见verification.json，原始日志的大小/SHA见local-log-index.csv；原始文件在B本机被忽略的runs目录，不表示已上传给队友。

## 覆盖与边界

- 教师集合：空、无idle、双idle、不同分数的重复发送键、不可行idle均拒绝；合法idle-only和不可行发送标签保留。
- 显式边界：validate_teacher_result重验Observation与TeacherResult，队列外任务受控拒绝；已有模型被修改后也不能绕过。输入不被修改。
- 预测版本：Python/JSON两种输入均拒绝部分或全部窗口的混批；空窗口及多个同版本窗口合法。
- 指标：14个可缺测指标逐个验证非null携带原因应拒绝，包括真实数值0；null有原因通过、null无原因失败。
- A模块、C页面、旧资产和历史A1证据未在本次修复中改动；Schema版本与HTTP错误码未增加。

环境沿用R0/H00：Windows、Python 3.12.14、NumPy 2.1.3、PyTorch 2.5.1+cpu、pytest 8.3.5、Pydantic 2.12.3、jsonschema 4.25.1，本轮无新增依赖。资产已按A提交的仓库内gitignore布局恢复，详情见`docs/handoffs/B_sync_2026-10-29.md`。

独立技术审查结论记录于review.md。独立审查不等于A/C签收，H00仍须按`docs/handoffs/H00_revision_2026-10-29.md`复测后决定是否冻结。
