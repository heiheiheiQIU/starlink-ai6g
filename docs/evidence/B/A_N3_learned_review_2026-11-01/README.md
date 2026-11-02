# B learned独立验收证据

候选固定为11c00374d88dbbc5138c7b2c65029317befa989c。

- targeted.xml：B实际46 passed（组合定向），1条既有Starlette/AnyIO警告。
- full.xml：B实际501 passed，同一警告。
- audit.py及verification.json：20观测正常推理、独立train归一化重算、validation选seed核对、inflight mask/空任务idle、缺文件/错hash/非ZIP文本/NaN/非法输入，以及网关异常与超时回退和1000次warm计时。
- test_corrupt_npz.py及corrupt_npz_red.xml：额外坏ZIP容器回归，1 failed，实际泄漏zipfile.BadZipFile；不在原501项范围内。

verification.json的format检查是非ZIP文本导致的ValueError转换，不能据此认为真正坏ZIP也已受控；正式验收结论以A_N3_learned_B_2026-11-01.md为准，为changes_requested。正常包通过与新增边界失败两类证据同时保留。

冻结原包审计后再次执行五SHA/8数组/配置和补丁身份预检仍通过，未改权重或训练配置。测试产物仅在隔离副本runs下生成。
