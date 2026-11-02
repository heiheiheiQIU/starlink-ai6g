# B API 状态读取补丁 A 侧接收回执

日期：2026-11-01（Asia/Shanghai）
接收人：A
来源提交：`576eb48f5d87abf8a0969b7c54df417523a39ee0`
来源分支：`origin/feature/shared-channel-r5`
应用目标：`codex/a-n3-learned`
应用提交：`3ea06f60b13cb036ca96ddd133345bf229d80aa0`
结论：**accepted for A-N3 integration**

## 接收范围

本次只接收 `minimal_api_read_retry.patch` 中的三条路径：

- `backend/api/worker.py`：新增 2 秒有界 `PermissionError` 读取重试。
- `backend/api/service.py`：`status()` 与 `reap()` 通过该 helper 读取 `status.json`。
- `tests/test_api_read_retry.py`：覆盖短锁恢复、spawn 后 reap 以及持续锁预算耗尽。

没有接收 B 分支中的共享随机信道、seed、实验、模型或其他 R5 功能；没有修改公共 contracts/schema、A-N3 模型包或训练配置。

## 身份核对

应用前 SHA-256 与 B 的 `patch_identity.json` 一致：

| 路径 | 应用前 SHA-256 | 应用后 SHA-256 |
|---|---|---|
| `backend/api/service.py` | `9fcbb6c5058f0ae823d05efb750eac0fb0f562d58f0367a2ce3a3ca39cff325d` | `97dcf58d296cc8d28be87aa3aeeb6d27ca90c8cc3cff43e20213717ce36f11e9` |
| `backend/api/worker.py` | `5e2b410cdf116fdb431f8552d0b3cf05bcc7b0a3dc33b61dfd9f7eead6bb2dce` | `0d6255f20d46d320d254623deadaf52db691061a47c4972e6eb347d99cc99941` |
| `tests/test_api_read_retry.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `99ca96f421b28a311dbabd20ad33b53a5296d26e264bc3cbcd1081c5d963104c` |

`git apply --check` 返回 0，实际应用后的三条 SHA-256 与 B 证据逐项一致。

## A 侧组合验证

- B 指定 API 定向：`13 passed, 1 warning in 5.55s`。
- A-N3 + API 组合定向：`92 passed, 1 warning in 12.22s`。
- 最终组合全库：`501 passed, 1 warning in 26.05s`。
- warning 为 Starlette 对 AnyIO 旧别名的上游弃用提示，与本补丁无关。

冻结身份保持不变：

| 对象 | SHA-256 |
|---|---|
| `backend/contracts.py` | `78f783e8fb1f3ea25bf001a474eb4467e1bfcaee74888597901f2a4f352fd814` |
| `configs/schema.json` | `d1a19c098b8c69ba7ebefc19db60c1e3f0f321c38b5f669518e7f05676b89fcb` |
| `weights.npz` | `a5226264d3a60f7d858e4d410595668b44b8dbd4c9a8bfa05191c1fd80461e4a` |
| `normalization.json` | `5c5fd7e843817a63ed6c486ed1c2a525243a724a6573b01681e0aa53811d2449` |
| `training_summary.json` | `fc011b87f2fdeaa0c0cd74b1de7f573d352902098ea0ca83c06f182faab672a3` |
| `model_card.md` | `7574292556c2500451b326ecf0ab4e924790dc84924b2dab253d380fdfaf87d7` |
| `manifest.json` | `949370f65165437a95b5858b23103b6cac892913592d1a4b54a3d3d4d27445a8` |

## 边界

本回执只证明 B 的最小读侧补丁在 A-N3 组合版本上缓解短暂 Windows 文件共享冲突，并保持持续锁的有界失败。它不代表 B 已验收 learned 模型，也不代表持续超过 2 秒的锁必然恢复。
