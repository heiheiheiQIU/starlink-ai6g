# 公共接口合同 v1.0 候选基线

状态：H00候选实现已准备，**ready_for_review；A/C尚未签收，不能称为已冻结**。Python类型位于`backend/contracts.py`，JSON Schema位于`configs/schema.json`；TypeScript镜像仍由C实现。以09手册补充为准。变更清单见[CHANGELOG](CHANGELOG.md)，发送单见[H00交接](../handoffs/H00_contract.md)。

本次只交公共类型、结构/语义校验和手工样例；不包含仿真器、guard、教师求解器、健康估计器、HTTP服务或任何通信实验结果。

## 全局规则

- JSON字段使用`snake_case`；顶层带`schema_version="1.0"`。
- 时间`s`，功率`W`，能量`Wh`，速率`bit/s`，数据量`byte`；`1 Wh = 3600 J`、`1 byte = 8 bit`。
- 缺测用`null`并给`reason_code`；数值0只表示真实测得零。
- 策略只能读取`Observation`，不能读取未来任务、实际未来丢包、真实容量或环境内部状态。
- 同一run最多比较两个不同`policy_id`；全部策略使用相同配置、seed、预测与评价口径。

## 核心类型

`Task`：`task_id:str`、`arrival_s:float`、`deadline_s:float`、`payload_bytes:int`、`remaining_bytes:int`、`priority_weight:float`、`business_class:str`、`data_location:str`。首版位置固定`satellite_1`；payload/weight大于0，deadline大于arrival。

`Window`：`window_id:str`、`start_s:float`、`end_s:float`、`rate_profile:[{time_s,robust_bps,fast_bps}]`、`loss_profile:[{time_s,robust_loss_prob,fast_loss_prob}]`、`source:str`、`forecast_version:str`。区间为`[start,end)`，概率0—1，窗口外不可发。

`HealthEstimate`：`soc_est`、`soc_lower`、`capacity_Wh_est`、`capacity_lower_Wh`、`energy_lower_Wh`、`rul_est:null|float`、`rul_unit:null|str`、`uncertainty_method`、`model_version`、`observed_at_s`、`available_at_s`、`reason_codes:list[str]`。旧模型`raw_fraction`不得直接映射这些字段。

`InFlight`：`task_id`、`block_id`、`payload_bytes`、`mode`、`sent_at_s`、`timeout_at_s`、`retries`；不得包含“地面已收到但ACK未到”的真值。

`Observation`：`schema_version`、`run_id`、`policy_id`、`sim_time_s`、`tasks`、`forecast_windows`、`health`、`inflight`、`cache_bytes`、`forecast_version`。

`CandidateScore`：`task_id:null|str`、`mode:idle|robust|fast`、`score:float`。每次恰有一个idle候选；非idle必须引用当前队列任务。

`Action`：`task_id:null|str`、`mode`、`scheduled_bytes:int`、`reason_codes:list[str]`、`fallback:bool`。AI只评分，B的guard决定合法字节量。

`Decision`：`action`、`candidate_scores`（事件可只保存top3）、`constraint_checks`、`decision_latency_ms`、`fallback`、`model_version`、`policy_version`。

`Event`基础字段：`event_id`、`run_id`、`policy_id`、`sim_time_s`、`event_type`、`task_id`、`block_id`、`payload_bytes`、`overhead_bytes`、`energy_Wh`、`reason_code`、`data`。`event.energy_Wh`是本事件增量耗能，剩余能量只从snapshot读取。

展示事件：

- `decision.data`：`action,candidate_scores,constraint_checks,latency_ms,fallback,model_version,policy_version`。内部Decision保留`decision_latency_ms`，必须通过`Decision.to_event_data()`转换；线上仅接受09规定的`latency_ms`，不混用别名。
- `snapshot.data`：`soc_est`、`energy_est_Wh`、`energy_lower_Wh`、`queue_count`、`forecast_energy_band`、`policy_version`。事后真值放`evaluation_truth`并标`posthoc_simulation`，策略不得回读。
- `window_changed.data`：`window_id`、`is_visible`。

`RunResult`：`schema_version`、`run_id`、`status`、`config_hash`、`input_hash`、`model_hash`、`code_revision`、`seed`、`by_policy`、`metric_definitions`、`artifact_paths`。该类型专用于正式结果，status只允许`completed`。五种运行状态保留在`RunStatusResponse`中；未完成/失败的partial记录不能包装为RunResult。

## Python函数边界

```python
# A
estimate_health(history: list[dict], now_s: float) -> HealthEstimate
score_actions(obs: Observation) -> list[CandidateScore]

# B
observe(state: SimulatorState) -> Observation
decode_safe(obs: Observation, scores: list[CandidateScore]) -> Decision
step(state: SimulatorState, action: Action, dt_s: float) -> StepResult
solve_teacher(obs: Observation, budget_ms: int) -> TeacherResult
evaluate(events: list[Event], config: dict) -> dict
```

B集中定义公共类型。A不得另造同名不同字段类型；C不得从事件自行重算科学指标。A失败抛受控错误，B记录fallback事件。

## HTTP合同

| 请求 | 成功 | 失败 |
|---|---|---|
| `POST /runs` | 202 `{run_id,status:"queued",schema_version}` | 422非法；重复policy拒绝；容量不足429 |
| `GET /runs/{id}` | `{run_id,status,progress,active_policies,error}` | 404；progress为0—1或null |
| `GET /runs/{id}/events?after=&limit=` | `{run_id,events,next_after,has_more}` | 游标非法422；running也可读 |
| `GET /runs/{id}/results` | completed结果和指标定义 | 非completed返回409 |
| `GET /runs/{id}/export` | 完整run ZIP | 非completed返回409；禁止任意路径读取 |

错误统一`{code,message,details}`，至少包括`INVALID_CONFIG`、`RUN_NOT_FOUND`、`RUN_NOT_COMPLETE`、`CAPACITY_BUSY`、`INTERNAL_RUN_ERROR`。前端按code处理。

## 六个共同契约样例

1. 空队列：idle、0 byte。
2. 无窗口：非idle被拦截，`NO_VISIBLE_WINDOW`。
3. 能量不足：fallback/idle，`ENERGY_RESERVE`。
4. ACK丢失：重传但网关成功字节去重，首次完整接收时刻判完成。
5. 模型缺失/NaN：`MODEL_UNAVAILABLE`或`INVALID_SCORE`，规则回退。
6. 页面刷新：恢复相同run和事件游标，不创建新实验。

## 合同变更

提出者在`docs/handoffs/`写旧字段、新字段、原因、兼容性和受影响文件；B修改本合同及Python类型，A/C各跑至少一个契约样例并签收。破坏语义才升级schema；新增兼容字段也必须写CHANGELOG。未经流程的字段漂移必须拒收。

## 当前代码如何使用

依赖固定为Pydantic 2.12.3；jsonschema 4.25.1用于独立Schema测试校验。它们已记录到pyproject及requirements.lock.txt；后者仍是直接依赖清单，不是完整跨平台锁。

```python
from backend.contracts import Observation, validate_candidate_scores

obs = Observation.model_validate(observation_payload)
scores = validate_candidate_scores(obs, scorer_output)
# 后续由B实现的decode_safe决定动作；此处不执行任何发送。
```

所有边界模型严格检查类型、不接收额外字段、拒绝NaN/Inf；已有模型实例及其嵌套实例也重新校验，避免子类携带真值或实例被修改后绕过检查。整数byte、seed、event_id拒绝bool、字符串及浮点；JSON Schema把数学意义整数视为integer，而Python调用还要求实际int，因此客户端应序列化为整数字面量。

模型不是安全沙箱或深度不可变容器。调用者不得通过model_construct/model_copy(update=...)或随后修改容器绕过边界；交接时重新model_validate，环境观察生成器R2必须构造独立观测，不能把环境对象直接传入策略。

运行契约验证（无需加载旧资产）：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_contracts.py -q --noconftest -p no:cacheprovider
.\.venv\Scripts\python.exe -m backend.contracts --schema-output configs/schema.json
```

Schema是单一Python定义导出的Draft 2020-12 bundle；使用`$defs/Observation`、`$defs/Event`等命名定义。先修改类型/测试，再重新导出；不手工维护第二套Schema。内部`SimulatorState`及`StepResult`不进入JSON Schema。

## 补充字段字典与待三方确认的细化

这些是对09留白的候选细化，逐项列入CHANGELOG；不表示A/C已同意。

| 对象/字段 | 类型、单位及规则 |
|---|---|
| Task.remaining_bytes | int byte，0..payload_bytes；包含未获ACK确认的待发载荷，不借此透露网关去重状态 |
| Task时间 | 非负秒，deadline_s>arrival_s；Observation只含arrival_s<=sim_time_s的任务，不在H00判定业务完成 |
| Window profiles | 非空，首点time_s=start_s；严格递增且位于[start_s,end_s)；这里只校格式，不实现分段采样 |
| HealthEstimate | 0<=soc_lower<=soc_est<=1；0<=capacity_lower_Wh<=capacity_Wh_est且估计容量>0；energy_lower_Wh=soc_lower×capacity_lower_Wh，相对/绝对误差容差1e-9 |
| Health时间 | observed_at_s<=available_at_s<=Observation.sim_time_s；单位s。旧cycle/orbit索引不能直接填入 |
| 缺RUL | rul_est=null并提供reason_codes；rul_unit可null或保留已知原生单位；有RUL必须给单位 |
| InFlight.block_id | 非负整数，同任务内块索引；网关最终以(task_id,block_id)去重 |
| InFlight.payload_bytes | 1..1024，mode仅robust/fast；timeout_at_s>sent_at_s；不携带网关接收真值 |
| CandidateScore | idle的task_id=null，发送模式必须有task_id；score有限但可为负 |
| 完整候选集合 | 使用validate_candidate_scores检查恰好一个idle、无重复(task_id,mode)、非idle引用当前任务；失败抛ContractViolation(code=INVALID_SCORE)，回退由R4实现 |
| Decision候选摘要 | 可只含top3，允许无idle；不能把摘要传给完整评分校验器，也不能用摘要充当完整教师标签 |
| Action | idle为null任务/0byte，发送为有效任务/1..1024byte；fallback=true必须有原因。格式合法不等于能量/窗口可行 |
| ConstraintCheck | {code:str,passed:bool,details:JSON对象}；details只存约束解释，不假称模型自动推理解释 |
| EnergyBandPoint | {time_s,energy_lower_Wh,energy_upper_Wh}，非负且lower<=upper |
| SnapshotData | 09字段加evaluation_truth:null\|EvaluationTruth及reason_codes；缺forecast_energy_band时null+原因；energy_lower_Wh<=energy_est_Wh |
| EvaluationTruth | {label:"posthoc_simulation",soc_true,energy_true_Wh,capacity_true_Wh}；允许裁剪前负能量/负SOC证据，仅事后显示，不得回送策略 |
| Event.energy_Wh | 本事件增量消耗，不是剩余电量；所有字节字段非负，非适用字段null/0 |
| Event.data | decision/snapshot/window_changed按各自结构；基本传输事件为null。Event格式验证不推断交付、丢包或能量守恒 |
| EventsPage | event_id严格递增、不混run、next_after等于末事件ID；空页next_after保持原游标且has_more=false；不能按跨policy的sim_time_s排序 |
| RunRequest.config | 当前只检查JSON对象及有限数值；具体场景参数schema在R2定义。接受此封装不表示任意业务配置可运行 |
| RunStatusResponse | {run_id,status,progress,active_policies,error}；progress=null或0..1；failed必须有ErrorBody，其他状态error=null；最多2个不重复活跃策略 |
| ErrorBody | {code,message,details}；五个初始错误码与HTTP表一致；details为JSON对象，C按code处理 |
| TeacherCandidateScore | CandidateScore加feasible:bool；TeacherResult含candidate_scores、solver_status、gap:null或非负、elapsed_ms非负；版本在A样本元数据中记录，H02再定求解器状态映射 |
| SimulatorState | 环境专用Protocol，仅规定run_id/policy_id/sim_time_s；R2补具体隐藏真值实现，不是可构造的仿真环境或策略DTO |
| StepResult | 环境内部dataclass(next_state:SimulatorState,events:list[Event])；没有默认序列化到策略/API |

## 结果指标字段

`by_policy`为1—2个PolicyResult，policy_id不得重复。每项还包含model_hash（规则为null）、sample_count（纳入评价的到期任务数）、evaluation_end_s、pending_task_count、success_payload_bytes及metric_reasons。

| 字段 | 单位/含义 |
|---|---|
| weighted_on_time_rate | 0..1，纳入评价的任务按权重计算完整按时交付率；分母为空为null |
| critical_task_success_rate | 0..1，关键任务完整按时成功率；无关键任务时null+原因 |
| goodput_bps | 成功去重有效载荷bit/评价时长s；不是物理链路速率 |
| minimum_soc_true | 比例，环境真实最低SOC；预测约束通过不能替代此值 |
| energy_violation_count / energy_violation_duration_s | 次数/秒；具体连续违例计数在R3评价器固定 |
| joule_per_success_bit | J/成功有效bit；success_payload_bytes=0时必须null，metric_reasons对应值为NO_DELIVERY |
| wait_p50_s / wait_p95_s | 等待秒数；完整采样口径由R3/R7指标文档确定，不在浏览器另算 |
| decision_p50_ms / decision_p95_ms | 决策毫秒；后续计时含推理/解码/修复；P50<=P95 |
| timeout_rate | 0..1，决策超时比例 |
| parameter_count / memory_bytes | 模型参数个数/内存byte；无对应测量为null+原因 |

所有缺测指标必须为null且在metric_reasons中有同名原因；0只能表示已测为零。config_hash/input_hash及非null的model_hash为64位十六进制SHA256，但格式校验不证明内容真实，R5必须实际计算。混合模型对照时顶层model_hash=null，逐策略保留；相同模型才可用共同顶层hash。

artifact_paths只接受run内相对路径；R5导出还需检查解析后的路径及链接，不把字符串校验当完整文件访问保护。

## Schema与Python校验的边界

JSON Schema校验字段结构、基本类型、范围和事件payload变体；跨字段比较、时间顺序、任务引用、候选集合完整性、指标缺失原因及跨事件游标关系由Python校验。C使用Schema不能替代后端验证。标准JSON不允许NaN/Inf，运行时仍需拒绝它们。

`tests/fixtures/contracts/manifest.json`索引六个场景及合法/非法、HTTP和结果样例。每份有外层`kind=contract_fixture`及`is_experimental_result=false`；导入模型时取examples[].payload。样例的全零/全一哈希是占位符，绝不是实际实验哈希。

ACK丢失和页面刷新样例含expected_behavior且behavior_verified=false：本次验证的是A/C能解释并读取的格式，R3/R5/R6才验真实行为。不得用它们填充正式实验页面并标成实测。
