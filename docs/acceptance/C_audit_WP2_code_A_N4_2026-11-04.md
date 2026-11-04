# C 补记：WP2/A-N4 代码级复核完成（网络恢复后）

日期：2026-11-04。网络恢复后拉取远端，对 `origin/codex/b-wp2-learned-20261104@6051d34`（PR #11）与 `origin/codex/a-n4-data-audit@657f39c` 做代码级复核；此前仅审交接单的结论全部得到源码确认。

## 1. WP2 代码复核：通过（与交接单一致）

- **三策略白名单**：service.py `if any(p not in ('edf','value','learned'))` 校验，每请求≤2策略沿用原约束；含 learned 时创建前 `inspect_model` 全链路校验（manifest SHA 注册表=949370f6…、四产物哈希、运行时配置哈希一致、`_bundle` 形状/有限性）——任一失败 422 MODEL_UNAVAILABLE ✓；
- **回退语义**：runner 中候选键集合不符→INVALID_SCORE、全部发送候选被 mask→NO_VALID_CANDIDATE、其余异常→fallback_decision(EDF)；**RETRY_REQUIRED 以 reason_codes 追加方式覆盖动作，decision 保留模型原始评分**——协议义务不被模型绕过 ✓；
- **推理进程生命周期**：inference.py 注册表式冻结身份、启动 gate+父进程存活检查、ready 握手、budget 100ms、诊断计数器（fallback_reasons/successful_model_decisions/retry_override_count/cold_load_ms）完整 ✓；
- 测试面：test_inference_lifecycle/test_learned_api/test_learned_integration 等新回归齐全；B 的 552 后端/61 前端记录可信。

## 2. A-N4 数据审计：源码与 C 独立复算一致

- `training/audit_policy_dataset.py`＋`test_policy_dataset_audit.py` 已提交；七项结论（13/20 全零、19/20 idle 并列最优、1/20 唯一非idle 最优、三类困难工况 0 覆盖）与 C 独立复算完全一致；
- A 的结论"冻结包仅管线回归用途"成立。

## 3. B 对 A-N4b 的输入已闭环（teacher_support 确认）

- **reserve 语义精确化**：`允许发送 ⇔ energy_lower − cost ≥ reserve`，cost 含 base/compute 水平线＋tx＋ack 项；本轮参数下数学门槛≈0.5309027778 Wh，0.49/0.5/0.51 均拒绝；**A 采样用 ±1e-6 区分两侧、原样调用教师**；
- **首批扩样支持域**：1-4 任务/0-3 窗口/期限 0-30s/1-4096B/零损失/固定物理参数；**来源状态准入检查**（无 inflight、无 retry 义务、控制事件清空）归来源审计——防私有协议对象泄漏；
- A-N4b 新数据集生成的全部前置确认已具备，可开工。

## 4. C 裁定

- WP2：**C 代码级复核通过**（A 复测后即可视为三方齐）；B 可推进正式实验配置冻结（11/06 20:00）；
- A-N4：审计结论成立；A 可按 B 支持域确认启动新版本小批生成与审计（不覆盖旧数据）。
