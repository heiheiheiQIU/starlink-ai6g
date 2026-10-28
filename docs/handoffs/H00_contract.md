# H00公共合同候选交接

2026-10-29修订入口：[H00审查修复交接](H00_revision_2026-10-29.md)。A/C对旧提交的changes_requested已按三项要求修复，原文和旧证据保留历史条件；当前等待修复提交的新回执。

日期：2026-10-28（Asia/Hong_Kong）。B → A/C。任务B-N1/R1，schema_version=1.0，**ready_for_review，尚未accepted**。

## 交付范围

- `backend/contracts.py`：公共类型、候选输出校验、延迟字段转换、schema导出。
- `configs/schema.json`：生成的Draft 2020-12结构合同；与代码一致性由测试检查。
- `docs/contracts/README.md`、`CHANGELOG.md`：字段、单位、补充细化、校验边界及待确认点。
- `tests/test_contracts.py`：有效/非法输入、嵌套真值隔离、模型实例绕过回归、候选集合、分页和结果状态等契约测试。
- `tests/fixtures/contracts/`：六个场景及通用合法/非法、HTTP/结果样例，全部显式标非实验。
- `docs/evidence/B/H00_2026-10-28/`：测试摘要、复核记录、输入来源和交付文件SHA清单。

不交付：observe/step仿真实现、decode_safe策略约束实现、教师优化器、HTTP端点、A的健康/模型函数或C页面。这些签名在合同中保留，函数代码属于后续R2—R6。

## 如何读取与校验

在产品仓库根、安装更新后的requirements.lock.txt后运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_contracts.py -q --noconftest -p no:cacheprovider
.\.venv\Scripts\python.exe -m backend.contracts --schema-output configs/schema.json
git diff -- configs/schema.json
```

导出不应产生schema差异。H00测试不依赖legacy目录；若临时目录权限受限，追加一个新的工作区内--basetemp目录，不复用包含有价值文件的路径。

Python消费者使用`Model.model_validate(payload)`或`model_validate_json(text)`；Fixture外层是说明封装，实际载荷是`examples[].payload`。完整评分使用`validate_candidate_scores(obs,scores)`，Decision事件必须用`to_event_data()`生成线上latency_ms。

## A应执行的三个检查

1. 读取HealthEstimate/Observation/CandidateScore字段及单位；用正常、RUL缺失和未来健康样例确认语义。原生cycle/orbit不能冒充秒，raw_fraction不能冒充SOC。
2. 运行候选输出检查：恰好一个idle、无重复、无队列外task_id，NaN/Inf应受控失败；不从完整候选校验推断guard已实现。
3. 审查CHANGELOG中的首次细化，尤其健康下界、block_id、模型哈希及教师元数据边界；反馈模型/健康模块是否可据此实现，不代B实现环境。

## C应执行的三个检查

1. 用schema或自己的TypeScript类型读取六场景JSON，核对所有单位、null和理由码；保持“契约样例/非实验结果”标签。
2. 核对decision.data.latency_ms、snapshot电量字段和policy_id；event.energy_Wh不是剩余电量，evaluation_truth只能标事后评估。
3. 检查分页/刷新、未完成409、错误码与结果缺测展示规则；确认字段可用于页面，不把fixture行为视为API实测。

## 必须保留的限制

- A/C签收前不能宣布接口已经三方冻结；本单不是实际发出的外部消息。
- Schema验证结构，跨字段/时间/引用等验证见Python；场景config语义留R2，实际HTTP/导出安全留R5。
- 旧仓库资产默认路径问题仍存在，H00不私改A代码或团队默认配置；全库验证要区分主仓库失败与仅改路径的隔离验证结果。
- 具体测试计数、源码快照条件及日志哈希以配套证据报告为准；不沿用旧61项作为新H00证明。

回执位置：`docs/acceptance/H00_A_日期.md`、`H00_C_日期.md`，由接收人本人记录机器环境、文件SHA、命令、结果和accepted/changes_requested。当前不生成代签文件。
