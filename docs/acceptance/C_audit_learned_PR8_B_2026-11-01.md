# C 审计注记：B 对 PR #8 learned 包的正式验收（69847d8）

日期：2026-11-01 晚。对象：`origin/codex/a-n3-learned@11c00374`（PR #8）、`origin/feature/shared-channel-r5@69847d8`（B 验收）。

## 1. B 的 changes_requested：C 独立代码核对属实

B 唯一必修项 = `backend/policies/learned.py::_load_bundle` 的异常转换缺口。C 直接读 11c00374 源码确认：

- `_load_bundle` 的 except 元组为 `(OSError, ValueError, TypeError)`；
- 带 ZIP 签名但容器损坏的 npz 抛 `zipfile.BadZipFile`（继承自 Exception，不落入上述元组）→ **原样泄漏**，未转为约定的 `LearnedPolicyError(MODEL_FORMAT)`；
- B 用 `b'PK\x03\x04broken archive payload'` 构造真实损坏容器并绕过哈希检查复现（新增回归 test_damaged_zip_is_controlled_model_format 在候选上 1 failed）。

**修复范围极小**：except 元组加 `zipfile.BadZipFile`（建议同加 `EOFError` 防御截断文件）＋补回归。**无需重训、不改权重、不重新选seed**。

## 2. B 已通过的范围（46定向/501全库均为B实测）

- 五文件SHA+manifest、权重8数组名/形状/float32/有限性；20观测推理候选键完整、唯一idle、输入不变；inflight 发送候选=-1.0；无任务保留唯一idle；
- 归一化用 train 12样本独立重算一致；三seed按validation选20261033核对一致；冻结摘要一致（不重训不重选）；
- MODEL_UNAVAILABLE/MODEL_TIMEOUT 实际网关回退通过；B 独立计时冷载2.22ms、warm median 0.499ms；
- 诚实边界完整：test 4/4 与 idle 基线同样 4/4——**不构成泛化或收益结论**，正式实验须 EDF/value/learned＋优化器对照。

## 3. C 裁定与行动

1. B 的 changes_requested 成立且单一；A 今晚补加载器异常+回归+新SHA（15分钟级修改）；
2. B 复验该失败用例+正常包+回退后升级签收 → 接 learned 进五接口（B 已备好接入路径）；
3. **A 的 R2/R5 两份回执仍在本地分支 codex/a-r2-r5-receipts 未推送**——main 合并继续被卡，必须与修复一起推；
4. 节奏仍可控：今晚 A 修+推 → 明早 B 复验 → 明天白天接入 → 11/04 G4 有戏。
