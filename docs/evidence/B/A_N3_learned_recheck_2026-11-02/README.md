# B 修复版复验证据

候选 `1c90246376b91fb789154b22530b25bab2142b7e`，由 git archive 导出到 `runs/b_learned_recheck_20261102/source`。模型不重训，原始冻结包不修改。Python 3.12.14 / NumPy 2.1.3 / Pydantic 2.12.3。

本目录 check_package.py 与 audit.py 复用 11/01 验证逻辑，仅将固定候选 SHA 改成新 SHA；分别生成 intake.json 和 verification.json。intake 的 pending_functional_review 是该静态步骤的状态，最终结论以 11/02 B 签收回执为准。

执行命令（仓库根目录，PowerShell）：

```powershell
.venv/Scripts/python.exe docs/evidence/B/A_N3_learned_recheck_2026-11-02/check_package.py runs/b_learned_recheck_20261102/source docs/evidence/B/A_N3_learned_recheck_2026-11-02/intake.json
.venv/Scripts/python.exe docs/evidence/B/A_N3_learned_recheck_2026-11-02/audit.py runs/b_learned_recheck_20261102/source docs/evidence/B/A_N3_learned_recheck_2026-11-02
$env:B_LEARNED_SOURCE = (Resolve-Path runs/b_learned_recheck_20261102/source).Path
.venv/Scripts/python.exe -m pytest docs/evidence/B/A_N3_learned_review_2026-11-01/test_corrupt_npz.py -q -p no:cacheprovider --basetemp runs/b_learned_recheck_20261102/receiver_tmp --junitxml docs/evidence/B/A_N3_learned_recheck_2026-11-02/corrupt_npz_green.xml
```

在候选 source 目录，以 B 的绝对路径 .venv/Scripts/python.exe 执行（设置 GIT_CEILING_DIRECTORIES 为 source 父目录，防止引用外层 B 提交）：

```text
-m pytest tests/test_policy_dataset.py tests/test_policy_training.py tests/test_learned_policy.py tests/test_policy_runner.py tests/test_api.py tests/test_api_read_retry.py -q -p no:cacheprovider --basetemp ../target_tmp --junitxml ../../../docs/evidence/B/A_N3_learned_recheck_2026-11-02/targeted.xml
-m pytest -q -p no:cacheprovider --basetemp ../full_tmp --junitxml ../../../docs/evidence/B/A_N3_learned_recheck_2026-11-02/full.xml
```

旧资产按已有本地交付包建立 source/交付包 junction；其仅供测试配置读取，不修改资产。重跑时使用新 basetemp。

结果：receiver 1 passed，targeted 48 passed，full 503 passed。后两者各有一个既有 AnyIO 弃用警告。verification.json 含 20 观测、归一化、mask、故障与回退、1000 次 warm 延迟。原始 11/01 red XML 保留，构成接收人同用例前后证据。

readiness.json 固定远端来源、祖先关系及合并预演；received/ 保留 git show 取得的 A/C 原回执。主线未变，合并预演不等于集成测试。files_sha256.json 记录本目录除自身外的 SHA256。
