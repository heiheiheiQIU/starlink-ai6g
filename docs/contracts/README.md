# 公共接口合同 v1.0 候选基线

状态：H00待B实现，A/C评审。本文冻结名称、单位、缺失语义和HTTP行为；Python类型最终由B在`backend/contracts.py`实现，TypeScript镜像由C在`frontend/src/types/contracts.ts`实现。若实现与本文冲突，先修改合同并取得三方确认。

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

- `decision.data`：Decision字段。
- `snapshot.data`：`soc_est`、`energy_est_Wh`、`energy_lower_Wh`、`queue_count`、`forecast_energy_band`、`policy_version`。事后真值放`evaluation_truth`并标`posthoc_simulation`，策略不得回读。
- `window_changed.data`：`window_id`、`is_visible`。

`RunResult`：`run_id`、`status`、`config_hash`、`input_hash`、`model_hash`、`code_revision`、`seed`、`by_policy`、`metric_definitions`、`artifact_paths`。status仅`queued|running|completed|failed|cancelled`。

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
