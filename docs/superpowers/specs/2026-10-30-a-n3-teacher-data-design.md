# A-N3 教师数据、特征掩码与场景切分设计

日期：2026-10-30

角色：A
状态：待用户复核

## 1. 目标

基于已交付的 H02 教师接口，在不修改 B 的求解器、仿真器、guard 或公共合同的
前提下，完成 A-N3 第一阶段：

1. A 独立签收 `solve_teacher()` 并复算一条人工可解释标签；
2. 从 H02 的 20 个公开 `Observation` 重新调用教师，生成 A 自己的可追溯样本；
3. 定义只依赖公开观测的候选特征和结构 mask；
4. 按 `scenario_id` 冻结 12/4/4 的 train/validation/test 划分，证明集合无交叉；
5. 为 2026-10-31 开始的小 MLP 训练提供经过验收的输入，但本阶段不训练模型。

该阶段不宣称学习策略已经形成、策略优于规则、教师是全局优化器，或 20 个初始
状态足以代表正式实验分布。

## 2. 固定上游与分支边界

- 实现分支：`codex/a-n3-teacher-data`。
- 基线：`930476667933ca5d307a11e2003a7a263541baa9`。
- 教师实现源提交：`cccca9892086522624a5979216d7a2ab73209803`。
- 教师版本：`bounded-forecast-r4-v1`。
- 正式调用：
  `solve_teacher(obs: Observation, budget_ms: int, *, config=None, diagnostics=None) -> TeacherResult`。
- 输入观测来源：
  `docs/evidence/B/H02_2026-10-29/samples.jsonl`，但只读取每行的
  `sample_id` 与 `observation`；不复制 B 已生成的候选分数作为 A 标签。
- A 不修改 `backend/contracts.py`、`configs/schema.json`、
  `backend/policies/teacher.py`、`backend/simulator/` 或 `backend/api/`。
- 分支在 B 的 R2→R3→R4 集成顺序完成前不合入 `feature/ai` 或 `main`。

基线环境为 Python 3.12.9；锁定依赖通过 `pip check`；基线全库结果为
`293 passed, 1 warning`。唯一警告是已知 Starlette/AnyIO 弃用提示。

## 3. 方案选择

采用“重新求解 H02 的 20 个公开观测”方案，而不是直接复制 B 的标签，也不由 A
另造一套仿真环境。

- 直接复制 B 的 `candidate_scores` 无法证明 A 能独立消费 H02。
- A 自建环境或教师会越过 B 的文件所有权，并可能产生第二套口径。
- 重新调用冻结接口既能形成独立证据，也能让后续训练严格依赖公共合同。

## 4. 组件与文件职责

### 4.1 `training/generate_teacher_data.py`

负责读取 20 个源观测、验证、调用教师和写入 A 数据集。它不得导入
`SimulatorState`、环境 `step()`、真实能量账本或评价真值。

公开入口：

```python
generate_teacher_dataset(
    source_path: Path,
    output_dir: Path,
    *,
    budget_ms: int,
    source_revision: str,
) -> dict
```

CLI：

```powershell
python -m training.generate_teacher_data `
  --source docs/evidence/B/H02_2026-10-29/samples.jsonl `
  --output data/teacher/a_n3_20 `
  --budget-ms 1000 `
  --source-revision cccca9892086522624a5979216d7a2ab73209803
```

输出：

- `data/teacher/a_n3_20/samples.jsonl`：20 条完整重算记录；
- `data/teacher/a_n3_20/summary.json`：状态计数、准入计数、总 CPU/壁钟信息；
- `data/teacher/a_n3_20/manifest.json`：源、配置、代码和产物哈希；
- `docs/acceptance/H02_A_2026-10-30.md`：A 的独立接收回执，人工填写实际结果。

数据生成器不自动写回回执，避免程序替接收人签字。

### 4.2 `training/policy_features.py`

负责把一个 `Observation` 转为固定顺序的候选特征和结构 mask。它只做输入编码，
不调用教师、不调用 guard、不决定实际发送字节。

公开入口：

```python
encode_observation(obs: Observation) -> EncodedObservation
```

`EncodedObservation` 包含：

- `candidate_keys: tuple[tuple[str | None, str], ...]`；
- `global_features: tuple[float, ...]`；
- `candidate_features: tuple[tuple[float, ...], ...]`；
- `candidate_mask: tuple[bool, ...]`；
- `feature_names`、`global_feature_names` 和 `schema_version`。

候选键固定排序：按 `task_id` 字典序，每个任务依次 `robust`、`fast`，最后唯一
`(None, "idle")`。训练标签通过候选键关联，不依赖教师返回列表的偶然顺序。

### 4.3 `training/splits.py`

负责按场景而不是按样本行切分。公开入口：

```python
build_split_manifest(
    samples_path: Path,
    output_path: Path,
    *,
    split_seed: int,
) -> dict
```

对 20 个唯一 `scenario_id` 计算
`sha256(f"{split_seed}:{scenario_id}")` 并按摘要排序；前 12 个为 train，中间 4 个
为 validation，最后 4 个为 test。manifest 一经签收即冻结；同一场景未来增加的
多个状态必须查表进入同一集合。增加新场景时发布新 manifest 版本，不静默重新洗牌。

### 4.4 配置与测试

- `configs/policy_train.json`：记录数据版本、教师版本、`budget_ms=1000`、
  `split_seed=20261030`、12/4/4 计数、特征顺序和 mask 版本；
- `tests/test_teacher_data.py`：数据生成、准入、泄漏、哈希和输入不变测试；
- `tests/test_policy_features.py`：候选顺序、特征、mask、NaN 和空队列测试；
- `tests/test_splits.py`：场景级切分、固定计数、交集为空和确定性测试。

## 5. 样本记录合同

每行 JSON 包含：

```text
schema_version="1.0"
dataset_version="a-n3-teacher-20-v1"
sample_id
scenario_id
state_id
source_revision
source_observation_sha256
observation
teacher_version
teacher_config_sha256
candidate_scores
solver_status
gap
elapsed_ms
diagnostics
label_eligible
exclusion_reasons
label_content_sha256
```

规则：

- `scenario_id = observation.run_id`；`state_id = sample_id`；两者必须是非空字符串。
- `Observation.model_validate()` 必须成功，输入对象在调用前后逐字节规范化结果相同。
- `validate_teacher_result(observation, result)` 必须成功。
- `candidate_scores` 必须含唯一 idle，候选键唯一，所有 score 有限。
- 只有 `solver_status == "OPTIMAL"` 且 `gap == 0.0` 的记录可设置
  `label_eligible=true`。
- TIME/NODE limit、UNSUPPORTED 和受控失败全部写入数据集并给
  `exclusion_reasons`；禁止静默删除困难状态。
- 批次只有在 20 条全部生成且 20 条均准入时状态才是 `ready_for_split`；否则保留
  产物并将批次标为 `blocked`，不得开始训练。

`elapsed_ms` 是真实壁钟诊断值，会随运行变化。`label_content_sha256` 对去掉
`elapsed_ms` 和生成时间后的规范记录计算，证明标签内容可复算；manifest 另记录本次
实际文件 SHA256。两种哈希不能混称。

所有 JSON 使用 UTF-8、LF、`sort_keys=True`、`allow_nan=False`，文件以一个 LF
结束。输出目录必须不存在或为空，防止不同批次混写。

## 6. 特征和 mask 合同

### 6.1 全局特征

固定顺序：

1. `sim_time_s`
2. `cache_bytes`
3. `energy_lower_Wh`
4. `soc_lower`
5. `capacity_lower_Wh`
6. `visible_task_count`
7. `inflight_present`
8. `next_window_start_delta_s`
9. `next_window_duration_s`
10. `next_robust_bps`
11. `next_fast_bps`
12. `next_robust_loss_prob`
13. `next_fast_loss_prob`
14. `has_forecast_window`

“next window”只从 `forecast_windows` 中选择 `end_s > sim_time_s` 的最早窗口；当前
已打开窗口的 start delta 为 0。没有预测窗口时，窗口数值填 0 且
`has_forecast_window=0`；存在时该值为 1。禁止读取 true windows。

### 6.2 候选特征

固定顺序：

1. `is_idle`
2. `is_robust`
3. `is_fast`
4. `time_since_arrival_s`
5. `time_to_deadline_s`
6. `payload_bytes`
7. `remaining_bytes`
8. `remaining_fraction`
9. `priority_weight`

idle 的任务相关数值全为 0。所有数值必须有限；发现 NaN/Inf 或合同外负值时抛受控
`PolicyFeatureError`，不产生默认分数。

### 6.3 mask 语义

mask 只表达从当前公开 `Observation` 可以确定的结构可用性：

- idle 始终为 `True`；
- 无 inflight 时，可见、未过期且 `remaining_bytes > 0` 的任务，其 robust/fast
  候选为 `True`；
- inflight 存在时，所有非 idle 候选为 `False`；
- mask 不读取 `TeacherCandidateScore.feasible`、教师 score、环境真值或 guard
  内部状态。

教师的 `feasible` 只作为标签元数据保存。最终执行仍必须通过 B 的 `decode_safe`
和 guard；mask 为 True 不代表物理可执行或真实安全。

## 7. 防泄漏与来源检查

在序列化记录上递归拒绝以下字段名及其大小写变体：

- `true_capacity`
- `capacity_true_Wh`
- `future_arrivals`
- `actual_future_loss`
- `evaluation_truth`
- `energy_true_Wh`
- `soc_true`

此外：

- 生成器只能接收 `Observation`，不能接收 `SimulatorState`；
- 不把 B 的预跑 `candidate_scores` 当作新标签；
- 不从事件日志反推教师输入；
- 不把 synthetic 场景写成真实卫星测量；
- 不把 `OPTIMAL` 解释为真实环境全未来最优，只表示冻结有限预测模型的搜索状态。

## 8. 错误处理

- 源文件不存在、非 JSONL、重复 `sample_id`/`scenario_id`、记录数不为 20：生成前
  失败，不写正式 dataset manifest。
- 单条 Observation 或教师结果无效：写入受控失败记录和 summary，批次标
  `blocked`；其余记录继续生成以保留失败比例。
- 非 OPTIMAL：保留原始结果，`label_eligible=false`。
- 教师抛出未预期异常：记录异常类型，不写堆栈或本机隐私路径到正式样本。
- 输出已含文件：拒绝覆盖。
- split 输入不是 `ready_for_split`、不是 20 个唯一场景或存在非准入标签：拒绝生成
  正式 split manifest。

## 9. 测试策略

严格测试先行，至少覆盖：

1. 第一条 H02 观测重新求解后为 OPTIMAL、gap=0，T1/fast 得分 1.0，T1/robust
   不可行，且输入不变；不比较 `elapsed_ms`。
2. 20 条样本均实际调用 `solve_teacher`，不是复制源标签。
3. 同输入、同教师配置两次运行的候选键、score、status、gap 和
   `label_content_sha256` 相同。
4. 非 OPTIMAL、UNSUPPORTED 和异常记录保留且阻断训练准入。
5. 递归泄漏字段检测覆盖顶层和嵌套字典。
6. 空队列只有唯一 idle 且 mask=True。
7. inflight 时非 idle mask 全 False；教师 feasible 不影响 mask。
8. 候选排序与输入任务顺序无关，标签按键正确对齐。
9. NaN/Inf 特征受控失败。
10. 12/4/4 切分精确、三集合交集为空、并集等于 20 个场景；同一场景多状态不跨集。
11. manifest 中源观测、教师配置、源码和产物 SHA256 全部可复算。
12. 原 H02 定向测试与全库回归继续通过。

## 10. 验收与交接

H02 A 回执至少记录：上游/教师 SHA、Python 与依赖、独立一条标签、20 条状态统计、
测试命令、实际哈希、限制和 accepted/changes_requested。B 复核以下三项：

1. 任取一条样本，重新调用教师后标签内容一致；
2. 20 个场景切分无交叉，非准入记录没有进入训练集合；
3. 特征和 mask 仅依赖公开 Observation，最终动作仍由 guard 约束。

只有 B 签收样本和 split 后，才进入训练计划。模型结构、损失、checkpoint、三种子、
模型卡和 `backend/policies/learned.py` 属于下一阶段规格，不在本设计内。

## 11. 非目标

- 不扩到 500/2000 场景；
- 不实现或替换 B 的教师、guard、环境、规则策略或 API；
- 不训练 MLP，不生成权重，不发布 H04；
- 不把教师 elapsed_ms 当模型性能指标；
- 不用测试集选择特征、切分或未来 checkpoint；
- 不修改 legacy 原件或把旧模型结果冒充新训练成果。
