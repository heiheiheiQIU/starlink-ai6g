# B 最终来源文件与冻结回执交接 · 2026-11-10

最新状态见 [授权代审与 540 次全量结果](B_delegated_formal_results_2026-11-10.md)。下文为代审授权前的历史交接记录。

状态为 B_signed_AC_pending。B 已接收 A 的来源复核和 C 的库存复核、来源审计及最终字节提案，并签署绑定最终提案 SHA 的本人正式冻结回执。

## 实际交付

| 对象 | 路径或身份 |
|---|---|
| 正式源码提交 | 48157a8f4a1cdd7770685b79deb3fe4524b1bf7d |
| 180 候选清单 SHA | 2b0814db44b7c70cd94e44608e34c762ffaa86969ea6f955e4736b7b3cdcd31f |
| 最终来源字节提案 SHA | e8da2be7968020eb9d1e974ae1cd5b46d3ca89ebec3fab466750bc4df7747018 |
| 来源提案大小 | 33,328 bytes |
| B 本人正式回执 | [proposed_review/B.json](../evidence/B/formal_v2_finalization_2026-11-10/proposed_review/B.json) |
| 实际来源文件及待签 A/C 模板 | [proposed_review](../evidence/B/formal_v2_finalization_2026-11-10/proposed_review/leakage.json) |
| A/C 原始审核材料及提交身份 | [status.json](../evidence/B/formal_v2_finalization_2026-11-10/status.json) |
| B 新鲜核验结果 | [readiness_verification.json](../evidence/B/formal_v2_finalization_2026-11-10/readiness_verification.json) |

B 按 C 在 637c573 的提案，仅将既有来源草稿顶层 status 从 pending 改为 accepted，按 UTF-8、排序键、两空格缩进及结尾单个 LF 生成。长度和 SHA 与 C 提案逐字节一致。该目录是供 A/C 最终确认和签署的独立审查工作集，保留原候选包及旧草稿作为历史依据。

在单独检出的 48157a8 上，B 已重新验证 180 候选、三份生成前回执、当前源码、模型、统计规则和 binding，以及七个来源副本的 SHA。B 正式回执的角色、审核人、时间、binding 和最终 leakage_sha256 均已填写。运行索引工具实际返回 Receipt pending or subject mismatch: A，退出码 1，review.json 尚未生成。[门禁日志](../evidence/B/formal_v2_finalization_2026-11-10/index_gate.log)

## 下一步接收与签署

1. A 确认上述 e8da2be7 开头的完整最终 SHA，并在 proposed_review/A.json 填写本人 status、reviewer、reviewed_at、notes 和 leakage_sha256。
2. C 在收到 A 对最终字节的确认后，在 proposed_review/C.json 填写本人正式回执，绑定同一个完整 SHA。
3. 三方以本目录的同一 binding 和来源副本交接。任何最终来源文件字节变更都需要三份回执重新绑定。
4. B 核对收到的 A/C 原始提交及 SHA，运行 index、freeze 和 verify，通过后开始正式预跑。

A 11666cc 的人工来源回执和 C d98052d、637c573 的复核已接收。B 的新工作集完整保留其原始字节。C 提及的 A 124 项测试计数待 A 补命令或原始日志，本交接采用可复核的对象哈希及 B 本次实际运行的门禁结果。

## B 后续执行命令

以下操作在冻结代码工作区执行，Python 和证据目录均使用绝对路径。当前本机位置如下。

```powershell
$python = 'D:/人工智能挑战赛/starlink-ai6g/.venv/Scripts/python.exe'
$packet = 'D:/人工智能挑战赛/starlink-ai6g/docs/evidence/B/formal_v2_candidate_2026-11-09'
$review = 'D:/人工智能挑战赛/starlink-ai6g/docs/evidence/B/formal_v2_finalization_2026-11-10/proposed_review'
Set-Location 'D:/人工智能挑战赛/formal-frozen-verification-20261109'
git rev-parse HEAD
& $python -m scripts.prepare_formal_v2_review --index $review
if ($LASTEXITCODE -ne 0) { throw '三方回执门禁尚未通过' }
& $python -m backend.formal_freeze --candidate "$packet/candidate/manifest.json" --review "$review/review.json" --output runs/formal_v2_frozen_20261110
if ($LASTEXITCODE -ne 0) { throw '正式冻结失败' }
& $python -m backend.formal_freeze --verify runs/formal_v2_frozen_20261110/manifest.json
if ($LASTEXITCODE -ne 0) { throw '冻结包复核失败' }
```

冻结后沿用 backend.formal_experiments 的 smoke、cell、coverage、full 四段入口。所有分段复用同一个输出目录，后续段加 --resume。第一段覆盖 1 条 × 3 策略，第二段累计 1 格 × 10 条 × 3 策略。B 在前两段结束后记录墙钟、输出字节、成功/失败数量，以单写入器并发 1 估算全量完成时间和空间，再启动 coverage、full。首次失败和预登记的最多一次重试写入同一台账。

最终将 run_index.jsonl 输入 experiments.analyze_formal，保留两组配对差、18 工况等权汇总、分层样本及缺失、10000 次 bootstrap 区间、能量违规、回退和时延。结果审签前 formal_verdict 保持未完成，供 A 独立复核、C 登记 claim 后再进入正式材料。

## 本轮状态

正式冻结和正式策略运行均尚未执行，实际计数为 0/540。当前外部依赖是 A 对最终字节的确认，以及 A/C 各自的正式冻结回执。原始 Learned、模型和正式统计协议沿用已签对象。
