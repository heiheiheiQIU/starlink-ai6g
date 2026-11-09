# formal_v2 候选输入与第二阶段审查 · 2026-11-09

候选清单为 `candidate_pending_review`。在 `48157a8f4a1cdd7770685b79deb3fe4524b1bf7d` 核对三份原始回执后，B 用该提交的生成器生成了 180 份实际配置。策略运行数为 0。

## 生成前回执

| 对象 | 原始提交及路径 | 本包文件 SHA256 |
|---|---|---|
| A | `cf68a3b:docs/acceptance/B_formal_v2_generation_A_2026-11-07.json`，与 `c43978c` 的 B 目录副本逐字节一致 | `0f8fd89034231b2152f409b9e8acb5f70b6e800d4982d1b27b9c95ee25fa0535` |
| B | `c43978c:docs/evidence/B/sprint_2026-11-09/generation/B.json` | `e222957914e2613f95d343c4dcf6d27744b712e9a05eeb454e936fa5db04e597` |
| C | `564ed91:docs/acceptance/B_formal_v2_generation_C_2026-11-08.json`，与 `2aead7c` 的 B 目录副本逐字节一致 | `05b23e70551c2001b87240cc1d8e254cc00b27cf20cc94c09e70d1713387e867` |
| subject | `48157a8:docs/evidence/B/formal_v2_review_2026-11-07/generation/subject.json` | `936e5b2186bf6f0c65e10a3001b887d492ac85ffb54e65ced73ad72aad9346fe` |

## 实际候选与 B 核查

[候选清单](candidate/manifest.json) 的 SHA256 为 `2b0814db44b7c70cd94e44608e34c762ffaa86969ea6f955e4736b7b3cdcd31f`。[冻结审查对象](review/binding.json) 的 SHA256 为 `d2b596d852758c9514f2aa7b735f4cd1f31dbfbee0c23af50619fd51ecad5e2a`。候选目录包含登记协议、清单及 180 份配置。

[B 实际核查记录](B_inspection.json) 保存了 18 个工况的计数、五个模型文件的 SHA、代码身份与统计规则。180 份配置均通过运行配置校验，实际文件、场景和去标识内容的哈希逐一匹配。种子范围为 600000–600179，每个工况 10 条。EDF、Value 和 Learned 按同一轨迹读取同一份配置，对应 540 个不同的待运行键。

[泄漏审查草稿](review/leakage.json) 的 SHA256 为 `8bc1909e6d83f51c9a54813d989f4388c0d4aeb64ea5e00e793e717b06dbe0e8`。七个来源文件副本的 SHA 与冻结代码工作区中的文件一致。候选与退役、开发、先导来源汇总的 390 个不同种子、374 个不同场景内容哈希均无交集。180 个初始公开观测投影与旧教师的 20 个观测投影无交集。旧教师源缺少完整种子，A 仍需复核来源组和训练划分。

## 第二阶段接收

1. A 复核来源、划分以及实际交集，C 复核 180 条实际清单、三策略共享输入及 SHA。将实际审查结论写入 `review/leakage.json`，共同确认最终字节后计算 SHA256。
2. A、B、C 在各自的 `review/<角色>.json` 回执中填写本人审查结论、时间、状态和同一份最终泄漏文件的 SHA256。当前 B 已核对统计与运行对象，最终签名等待该 SHA。三份生成前回执仅用于生成本候选。
3. 在指定代码提交建立独立工作区，把本目录作为外部证据传给该版本工具。所有后续签核及冻结均使用绑定中的原代码提交。若直接在新增证据的提交上生成绑定，工具会读到不同的 Git 提交号。

以下 PowerShell 命令在单独检出的 `48157a8` 代码根目录执行。`$packet` 指向此证据目录的绝对路径，`$python` 指向项目既有虚拟环境的 Python。依次复验现有清单和生成一份新的待签审查副本，输出目录须为新目录。

```powershell
& $python -m backend.formal_v2 --verify "$packet/candidate/manifest.json"
& $python -m scripts.prepare_formal_v2_review --candidate "$packet/candidate/manifest.json" --output runs/formal_v2_review_recheck
```

最终三方回执经 `scripts.prepare_formal_v2_review --index` 接受后，按 [冻结与分段运行说明](../../../handoffs/B_remote_review_2026-11-07.md) 操作。正式输入冻结、预跑、540 次唯一策略运行和结果审签均在后续阶段。
