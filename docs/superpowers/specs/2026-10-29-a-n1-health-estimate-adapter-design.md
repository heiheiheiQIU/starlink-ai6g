# A-N1 正式 HealthEstimate 适配设计

日期：2026-10-29

角色：A

状态：设计已确认，等待书面规格复核

## 目标与前置条件

在已验收的A-N1合成健康估计内部核心外增加正式公共合同适配，使调用方可以使用冻结签名：

```python
estimate_health(history: list[dict], now_s: float) -> HealthEstimate
```

H00已通过`main@75f1c52`完成干净集成，`backend.contracts.HealthEstimate`为唯一公共返回类型。
本任务不复制或修改公共类型，不改变内部核心的计算、时间过滤、原因码和配置哈希语义。

## 范围与边界

本任务包含：

- 在`backend/health/estimator.py`增加两参数正式入口和公共类型转换；
- 增加可复现命令行调用入口；
- 增加正式适配测试；
- 生成成功、缺RUL说明和错误输入三类H01证据、调用日志与哈希清单；
- 将`docs/handoffs/H01_health_estimate.md`从内部草稿更新为待B验收的正式交接。

本任务不修改`backend/contracts.py`或`configs/schema.json`，不读取legacy未来标签，不把旧模型
`raw_fraction`映射为SOC、容量、能量或RUL，不训练新模型，不实施A-N2/A-N3，不生成真实卫星
测量或新实验性能结论。

## 方案选择

采用薄适配层方案：保留`estimate_health_core`及其内部dataclass，正式入口调用核心后逐字段构造
冻结的`HealthEstimate`。这样既保留已验收的A内部接口，又让B/C只消费H00公共类型。

不采用以下方案：

- 直接把内部核心返回类型改成公共类型：会破坏现有内部接口并扩大H00耦合；
- 新建一套独立解析器：会复制时间筛选和校验规则，形成两套可能漂移的实现。

## 公共入口与配置解析

公开函数严格只有两个参数：

```python
def estimate_health(history: list[dict], now_s: float) -> HealthEstimate:
    ...
```

配置固定为仓库内`configs/health_observation.json`。路径必须相对模块文件解析，不依赖当前工作目录：

```text
backend/health/estimator.py
  -> repository root
  -> configs/health_observation.json
```

正式入口每次读取并严格验证该文件，再调用`estimate_health_core`。首版不缓存配置，避免运行期间
文件内容变化却继续报告旧SHA；该文件很小，读取成本不构成当前瓶颈。测试可通过私有辅助函数显式
传入已验证配置，但不得扩大正式两参数签名。

## 类型转换与数据流

数据流固定为：

```text
history + now_s
  -> 固定配置加载与SHA256
  -> estimate_health_core
  -> HealthCoreEstimate
  -> 字段逐一映射
  -> backend.contracts.HealthEstimate二次验证
  -> 正式返回
```

字段映射如下：

| 内部字段 | 公共字段 | 规则 |
|---|---|---|
| `soc_est` | `soc_est` | 0—1比例 |
| `soc_lower` | `soc_lower` | 不高于估计值 |
| `capacity_Wh_est` | `capacity_Wh_est` | Wh且严格大于0 |
| `capacity_lower_Wh` | `capacity_lower_Wh` | Wh且非负 |
| `energy_lower_Wh` | `energy_lower_Wh` | 必须等于两个下界乘积 |
| `rul_est` | `rul_est` | 首版固定`None` |
| `rul_unit` | `rul_unit` | 首版固定`None`，不伪造cycle/orbit到秒的转换 |
| `uncertainty_method` | `uncertainty_method` | `synthetic_absolute_margin` |
| `model_version` | `model_version` | `synthetic-health-v1` |
| `observed_at_s` | `observed_at_s` | 秒 |
| `available_at_s` | `available_at_s` | 秒且不晚于调用时刻 |
| `reason_codes` | `reason_codes` | 转为公共合同的字符串列表 |

内部`config_sha256`不属于`HealthEstimate`字段，不塞入公共对象；它进入H01证据清单和调用日志。

## 错误处理

配置、history、观测、时间、无可用观测和歧义观测继续使用现有`HealthInputError`稳定错误码。
正式入口不得把错误回退为旧模型输出，也不得返回填0的伪健康结果。

如果内部结果意外无法构造冻结`HealthEstimate`，适配层将Pydantic合同错误转换为
`HealthInputError(code="HEALTH_CONTRACT_INVALID")`并保留异常链；这表示实现/合同不一致，
不是可降级成功。

## 命令行调用

在现有模块提供最小调用方式：

```powershell
python -m backend.health.estimator `
  --history <history.json> `
  --now-s <seconds>
```

`history.json`顶层必须是history数组。成功时标准输出只写一个公共`HealthEstimate` JSON；受控输入
错误时标准错误写`{"status":"rejected","error_code":...,"message":...}`并返回非零退出码。
日志和证据生成命令可以重定向该输出，但生产函数本身不写证据文件。

## 正式证据

新证据放在`docs/evidence/A/H01_2026-10-29/`，不覆盖
`docs/evidence/A1/`中的旧checkpoint证据：

- `health_success.json`：一次实际CLI成功调用的完整公共`HealthEstimate`；
- `health_missing_rul.json`：从同一成功调用生成的缺RUL审计视图，记录`rul_est=null`、
  `rul_unit=null`和原因码。它明确引用成功样例的输出SHA，不冒充第二次独立实验；
- `health_invalid.json`：一次实际CLI错误输入的受控拒绝结果及非零退出码；
- `smoke.log`：调用命令、Python/依赖版本、退出码和测试摘要；
- `manifest.json`：实现源码提交、固定配置SHA、规范化history输入SHA、各证据文件SHA和synthetic声明。

规范化history输入SHA对UTF-8、键排序、禁止NaN的JSON字节计算。`now_s`属于调用参数，另在manifest
明确记录，并与history共同计算`call_input_sha256`，避免相同history在不同时间被误认为相同调用。
manifest中的`source_revision`固定指向先完成并通过测试的实现提交；证据与交接随后单独提交，避免
把包含自身哈希的证据提交误写成被执行源码版本。

由于首版正式估计器始终缺RUL，`health_success.json`本身也合法包含`rul_est=null`；
`health_missing_rul.json`只是对该合同边界的专项验收视图，不能被宣传为另一个模型结果。

## 测试设计

严格按RED→GREEN实现，至少覆盖：

1. 正式入口返回实际`backend.contracts.HealthEstimate`实例；
2. 字段、Wh单位、时间、原因码及能量乘积与内部核心完全一致；
3. `rul_est`和`rul_unit`保持`None`且提供`RUL_UNAVAILABLE`；
4. 从仓库外工作目录调用时仍能读取固定配置；
5. 正常、未来记录、空history、非法字段、NaN/Inf和歧义记录保持受控错误；
6. 合同构造失败被包装为`HEALTH_CONTRACT_INVALID`；
7. CLI成功只输出合同JSON，错误输出受控JSON并返回非零；
8. 相同history与`now_s`重复调用得到相同公共结果；
9. 原内部核心测试、H00合同测试和A1 legacy测试全部回归通过。

## 分支与交接

实施前先把A开发基线更新到`origin/main@75f1c52`，只保留A自有提交；不得带入待B修复或待重新
验收的R3实现。公共合同文件保持逐字节不变。

完成后将正式适配、测试、三类证据、日志、SHA清单和更新后的H01交接提交给B验收。B应独立运行
一个成功、一个缺RUL检查和一个错误用例，并核对返回对象确为冻结`HealthEstimate`。
