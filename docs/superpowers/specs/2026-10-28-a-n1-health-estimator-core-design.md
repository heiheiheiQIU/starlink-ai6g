# A-N1 合成健康估计内部核心设计

日期：2026-10-28
角色：A
状态：设计已确认，等待书面规格复核

## 目标

在B的H00公共合同尚未冻结期间，实现A自有、无状态、可复现的健康估计内部核心。
它只消费明确标注为synthetic的SOC和容量观测，计算场景保守下界，不读取
`SimulatorState`、未来真值或旧模型`raw_fraction`，也不复制B拥有的
`backend/contracts.py`。H00冻结后再增加薄适配层，将内部结果转换为正式
`HealthEstimate`。

## 范围与文件

- 新建`backend/health/estimator.py`：配置解析、历史观测验证、时间筛选和保守下界计算。
- 新建`configs/health_observation.json`：冻结synthetic绝对误差参数。
- 新建`tests/test_health_estimator.py`：内部核心的单元与边界测试。
- 后续更新`docs/handoffs/H01_health_estimate.md`及正式样例；在H00冻结前只生成明确标注为
  `HealthCoreEstimate draft / 非正式公共合同`的证据。

本阶段不修改`backend/contracts.py`，不实现B的环境、guard或API，不训练容量头，不执行
A-N2校准或A-N3教师数据训练。

## 输入合同

公开的A内部签名固定为：

```python
load_health_observation_config(path: Path) -> HealthObservationConfig
estimate_health_core(
    history: list[dict],
    now_s: float,
    config: HealthObservationConfig,
) -> HealthCoreEstimate
```

两个返回类型均为本文件定义的不可变dataclass。`estimate_health_core`接收列表形式的
`history`，每条记录必须只包含：

- `source`：固定为`"synthetic"`；
- `soc_observed`：有限浮点数，范围0—1；
- `capacity_Wh_observed`：有限浮点数，单位Wh，严格大于0；
- `observed_at_s`：有限非负秒数；
- `available_at_s`：有限非负秒数，且不早于`observed_at_s`。

所有记录先做结构验证。额外字段一律拒绝，特别是`soc_true`、`capacity_true_Wh`、
`raw_fraction`等环境真值或旧模型输出。Python布尔值不能当作数值。`now_s`必须是有限、
非负秒数。

## 配置

`configs/health_observation.json`固定为：

```json
{
  "schema_version": "1.0",
  "method": "synthetic_absolute_margin",
  "soc_abs_error": 0.05,
  "capacity_abs_error_Wh": 1.0,
  "model_version": "synthetic-health-v1"
}
```

`soc_abs_error`必须为0—1有限数，`capacity_abs_error_Wh`必须为有限非负Wh，
`schema_version`、`method`和`model_version`必须与支持值完全匹配。配置保留原始文件SHA256，
用于证据和运行元数据。这些参数只是合成场景假设，不表示真实卫星传感器精度、统计置信区间
或校准覆盖保证。

## 时间选择与数据流

1. 解析并验证配置、`now_s`和全部历史记录。
2. 只保留`available_at_s <= now_s`的记录；合法未来记录不参与估计。
3. 按`available_at_s`最大、再按`observed_at_s`最大选择最新可用记录。
4. 如果最终时间键仍对应多条记录，返回`AMBIGUOUS_OBSERVATION`，不依赖输入顺序选值。
5. 如果没有可用记录，返回`NO_AVAILABLE_OBSERVATION`。
6. 对选中记录执行确定性绝对误差计算并返回冻结内部结果。

内部结果`HealthCoreEstimate`包含：

- `soc_est`、`soc_lower`；
- `capacity_Wh_est`、`capacity_lower_Wh`、`energy_lower_Wh`；
- `rul_est`、`rul_unit`；
- `uncertainty_method`、`model_version`、`config_sha256`；
- `observed_at_s`、`available_at_s`、`reason_codes`。

它是A内部不可变数据结构，不是B的公共`HealthEstimate`类型。

## 计算规则

```text
soc_est = soc_observed
soc_lower = max(0, soc_est - soc_abs_error)
capacity_Wh_est = capacity_Wh_observed
capacity_lower_Wh = max(0, capacity_Wh_est - capacity_abs_error_Wh)
energy_lower_Wh = soc_lower * capacity_lower_Wh
```

`uncertainty_method`固定为`synthetic_absolute_margin`，`model_version`取自配置。
由于旧RUL不能无泄漏恢复，首版固定：

```text
rul_est = None
rul_unit = None
reason_codes = [
  "SYNTHETIC_HEALTH_OBSERVATION",
  "SCENARIO_CONSERVATIVE_BOUND",
  "RUL_UNAVAILABLE"
]
```

输出不裁剪或解释旧模型`raw_fraction`，也不将cycle/orbit索引转换成秒。

## 错误处理

继续使用`backend.health.legacy_adapter.HealthInputError`，错误码至少包括：

- `HEALTH_CONFIG_INVALID`：配置缺失、额外字段、版本/方法不支持或数值范围错误；
- `NOW_S_INVALID`：当前时间不是有限非负秒数；
- `HISTORY_INVALID`：history不是列表或记录不是对象；
- `OBSERVATION_INVALID`：字段、单位、来源、范围、时间或有限性错误；
- `NO_AVAILABLE_OBSERVATION`：没有`available_at_s <= now_s`的记录；
- `AMBIGUOUS_OBSERVATION`：最新时间键存在多条记录。

错误不得静默回退为旧模型估计，不得用0代替缺失RUL，不得把失败记录为成功健康结果。

## 测试与验收

严格采用测试驱动开发，每项生产行为必须先有失败测试并确认因缺少实现而失败。首轮覆盖：

1. 正常观测生成确定性估计；
2. `soc_lower=0.5`、`capacity_lower_Wh=10`时`energy_lower_Wh=5Wh`；
3. RUL始终为`None`并带原因码；
4. 无序历史选择最新可用记录；
5. 合法未来观测不参与当前估计；
6. 只有未来观测时返回`NO_AVAILABLE_OBSERVATION`；
7. 最新时间重复时返回`AMBIGUOUS_OBSERVATION`；
8. NaN、Inf、布尔值、负时间、非法SOC/容量和错误source受控失败；
9. 额外真值字段和`raw_fraction`受控失败；
10. 配置范围、额外字段和SHA256稳定性；
11. 相同输入重复调用得到完全相同结果。

完成内部核心时运行`tests/test_health_estimator.py`及现有A测试。H00冻结后再补公共类型适配测试、
成功/RUL缺失/输入错误三份正式`HealthEstimate`样例、调用日志和H01交接，不把内部草稿冒充
正式合同交付。

## H00集成条件

只有当B修复A/C回执中的`TeacherResult`、预测版本和`metric_reasons`阻塞项，A/C重新签收且
H00合入`main`后，A才在此核心外增加正式适配函数。适配层只做字段转换和B模型验证，不能改变
核心计算、时间筛选、原因码或配置哈希。
