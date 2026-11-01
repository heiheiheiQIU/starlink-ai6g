# C 审计注记：B API 读取锁最小补丁（576eb48）+ learned 接收门状态

日期：2026-11-01 下午。对象：`origin/feature/shared-channel-r5@576eb48`。

## 1. 补丁代码复核：通过

`docs/evidence/B/API_lock_2026-11-01/minimal_api_read_retry.patch`：
- 只改 `backend/api/worker.py`（新增 `read_text`：PermissionError 有界重试、2秒预算、10ms间隔、超限原样抛出）与 `backend/api/service.py` 两处读点（reap 与 status 改用 read_text）；无业务逻辑、无 contracts/schema 变更；
- 新回归 `tests/test_api_read_retry.py` 三项：3次短锁后成功（4次尝试）、真实 spawn 进程退出后 reap 恢复、持续锁 ~2s 预算耗尽后抛原 PermissionError（虚拟时钟，不空等）——**有界退出语义诚实**（不是"绝对不锁"的假承诺）；
- B 实测表可信：A 基线复现 2 failed（PermissionError）、A+补丁 474 过、B 当前+新回归 312 过、状态/比较/分页/导出/刷新连续 20 轮 exit 0。

## 2. 对我此前审计注记的更正（诚实记录）

`C_audit_A_N3_learned_2026-11-01.md` 第2节曾写"B 的 service.py status/reap 读取路径未全覆盖"——**该结论只适用于 A 的旧基线（2cfe89c），不适用于 B 当前代码**（181dacc 自 5375e99 起已含 read_text 并接入 status/reap）。B 已用双侧验证澄清，本注记确认更正：**A 侧卡点 = 自身基线未含读侧补丁，应用最小补丁即可**，非 B 代码缺陷。

## 3. learned 接收门：awaiting_delivery 成立

- 远端仍无 `codex/a-n3-learned@97124d4` 与模型五文件（npz 被 gitignore，须另交产物）——B 无法独立验包，等待正确；
- B 已打破循环："A 不必等全库绿再交源码"——A 可先交只读 bundle/归档供 B 验包；
- B 的到件清单完整（五SHA/manifest、allow_pickle=False 验 float32/形状/有限性、定向复跑、12/4/4与归一化来源、回退注入、延迟实测）；B 明确"79/498/MSE/延迟仍是 A 记录，不写作 B 复验结果"——口径干净。

## 4. C 裁定与行动

1. B 补丁：**C 侧代码复核通过**；A 按交接单 `git apply --check` → apply → 定向+全库复跑 → 交最终 SHA；
2. A 立即交 97124d4（可推送评审分支或只读归档）＋模型五文件＋失败栈——**今晚必须**，否则 11/02 22:00 验收链紧张；
3. A 并行补交 R2 四项手算、R5 公平性两份回执（B 已确认 C 的 B1 accepted，该项不再阻塞）；
4. B 收到包后按清单独立验包＋接入 learned；C 待 A 推送后复核冻结包五SHA与 score_actions 代码。
