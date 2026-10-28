# H01 HealthEstimate交接草稿（A-N1内部核心）

日期：2026-10-28。状态：`internal_core_ready_for_review`，不是正式H01 accepted。

## 已交付

- `backend/health/estimator.py`：只消费明确标注为synthetic的SOC/容量观测。
- `configs/health_observation.json`：绝对误差场景参数及版本。
- `tests/test_health_estimator.py`：时间过滤、单位、下界、RUL缺失和错误边界。

内部入口：

```python
load_health_observation_config(path: Path) -> HealthObservationConfig
estimate_health_core(
    history: list[dict],
    now_s: float,
    config: HealthObservationConfig,
) -> HealthCoreEstimate
```

`HealthCoreEstimate`是A内部不可变结果，不是B的公共`HealthEstimate`。

## 数据与单位边界

- SOC是0—1比例；容量与能量单位为Wh；时间单位为秒。
- 只使用`available_at_s <= now_s`的synthetic记录。
- 下界采用配置中的确定性绝对误差，只能称为场景保守边界。
- `energy_lower_Wh = soc_lower * capacity_lower_Wh`。
- RUL固定为null；旧`raw_fraction`不进入SOC、容量或能量计算。

## 复现

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_health_estimator.py -q `
  --noconftest -p no:cacheprovider --basetemp runs\h01_draft_test\pytest
```

配置SHA256由`load_health_observation_config`从原始JSON字节计算并随结果返回。

## 尚未交付

- 尚未导入或复制B的`backend/contracts.py`。
- 尚未生成正式`HealthEstimate`成功、RUL缺失、输入错误三份样例。
- 尚未完成B主验或C字段展示检查。

以上工作等待H00阻塞项修复、A/C重新签收并合入`main`后完成。当前草稿不得用于宣称
在线健康校准、真实传感器精度或新通信实验结果。
