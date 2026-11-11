```text
A_ruling=accepted_with_notes
machine_audit.status=passed
```

# A 正式结果发布复核记录（2026-11-11）

A 接受本批冻结结果的事实与负统计结论，附带下述范围限制。此裁决只授权 B 合并 A/C 复核后生成单独、受门禁的统一发布摘要；它本身不批准发布，不翻转原始 `result_signoff=pending`，不改写原始 `formal_verdict=未完成`。**统计结论：负；原始发布状态：pending／复核中。**

## 复核对象与不可变绑定

本记录消费 Task 1 canonical JSON：[A_formal_results_audit.json](../evidence/A/formal_results_2026-11-11/A_formal_results_audit.json)，其文件字节 SHA256 为 `3e66408b832462111dbdd538aa8fe4e0f782c2461bd68bbd668915e3d36f0fd9`。该 JSON 中 `A_ruling=pending`、`release_approved=false` 是机器审计产物的状态，本记录不修改该产物。

下表 B 路径均相对 `docs/evidence/B/delegated_execution_2026-11-10/`，通过 B 证据提交的 Git blob 只读核验 SHA256。模型文件在冻结源码的 `artifacts/models/a_n3_policy_v1/` 下核验，并与 frozen manifest 中 `model/` 对应绑定一致。

| 对象 | 路径／身份 | SHA256 或 Git revision |
|---|---|---|
| B 证据提交 | source_commit | `a4890579f1d4a2cfb5be9246db6ca46a306fcd39` |
| 结果 ZIP | `formal_v2_delegated_results_20261110.zip` | `efa801d9dde6a9eb340ca0a27b873027248edbcadd7b85c82cdd3847ab5f9e86` |
| 原始 summary | `analysis/summary.json` | `872a71029783ca4100ed8d4e6cfec79261f9c7eaaca65b10362ce53a9ffdbae9` |
| 冻结 manifest | `frozen_manifest.json` | `3ad4bfeaf5398012bae17cab4bf684fb5a80ce0b5e341bf5e9eda4d179104d30` |
| run index | `run_index.jsonl` | `5d9c58585cd6782c3d898f2fc690829ae3a04956f9844e9ad6c389ea7d408ade` |
| 冻结源码 | code_revision | `48157a8f4a1cdd7770685b79deb3fe4524b1bf7d` |
| 模型版本 | model_version | `a-n3-mlp-v1` |
| 模型权重 | `weights.npz` | `a5226264d3a60f7d858e4d410595668b44b8dbd4c9a8bfa05191c1fd80461e4a` |
| 归一化 | `normalization.json` | `5c5fd7e843817a63ed6c486ed1c2a525243a724a6573b01681e0aa53811d2449` |
| 训练摘要 | `training_summary.json` | `fc011b87f2fdeaa0c0cd74b1de7f573d352902098ea0ca83c06f182faab672a3` |
| 模型卡 | `model_card.md` | `7574292556c2500451b326ecf0ab4e924790dc84924b2dab253d380fdfaf87d7` |
| C 复核记录提交 | `docs/acceptance/C_formal_results_release_review_2026-11-11.md` | `d9673126b41a678b6f83142b258fb4e8475d0bb5` |

C 记录中的 ZIP、summary、源码和权重绑定与上表相同。A 的裁决依据为 canonical 机器审计、冻结模型资料及直接绑定证据；C 记录仅用于确认同一复核对象与后续交接，不代替 A 的判断。

## 已验证事实与解释

| 已验证事实（证据来源） | A 的解释与适用限制 |
|---|---|
| canonical JSON：18 工况 × 10 轨迹 = 180 轨迹；三策略各 180 次，共 540/540 完成；attempt=1，failures=0、missing=0、retries=0。 | 技术执行完整，不意味着 Learned 获得正收益，也不等于发布完成。 |
| canonical JSON：冻结 `a-n3-mlp-v1` 权重身份一致；2160/2160 决策选择 idle，fallbacks=0；所有记录决策均由有限最大分数选择 idle。 | 全 idle 是模型评分选择的观测，不应解释为加载失败、模型缺失或 Guard fallback。 |
| canonical JSON：2009 次含 send 候选的决策，idle−best-send 分差最小 `4.4170640478569105e-08`、中位 `0.1785290241241455`，zero_count=0；另 151 次仅有 idle。 | 有发送候选时 idle 严格最高；仅 idle 的决策不能用作发送候选评分优劣的比较。 |
| 冻结模型卡／训练摘要：12/4/4 小样本划分，选中 seed=20261033；train utility MSE=`5.849076778474682e-11`，optimal-set hits=12/12；validation feasibility accuracy=`0.6000000834465027`、utility MSE=`0.3181956708431244`、total loss=`5.407445311546326`；test feasibility accuracy=`0.6666667461395264`、utility MSE=`0.356253057718277`。 | 训练拟合很强但验证／测试可行性与效用指标较弱；训练 optimal-set 命中不能当作正式策略收益。 |
| canonical JSON 与原始 summary：登记域为 `synthetic_out_of_zero_loss_training_domain`，source=synthetic；不是真实卫星测量，不是通用 policy benchmark。 | 小样本过拟合与域偏移是有证据支持的保守 idle 饱和贡献因素；没有受控因果实验，不能断言已证明原因，更不能推出所有学习方法均失败。 |
| 原始 summary：`safety_energy_violation_segments` 中 EDF=0、Value=0、Learned=0，总计 0 energy violation。 | 只陈述本批记录无能量违规；idle 的零违规不构成任务效用优势或真实部署安全保证。 |

## 三策略指标与负比较

指标为本批平均 weighted on-time rate，保留负结果与全部三策略，不用补训或替换模型改变结果。

| 策略 | 运行数 | weighted on-time rate |
|---|---:|---:|
| EDF | 180 | 0.4653873291265777（46.54%） |
| Value | 180 | 0.511472638980967（51.15%） |
| Learned | 180 | 0.0（0%） |

| 配对比较 | 配对数 | 均值差 | 95% CI | 统计结论 | 原始 formal_verdict |
|---|---:|---:|---|---|---|
| Learned−EDF | 180 | -0.4653873291265777 | [-0.49422782912931634, -0.43592598002654237] | 负 | 未完成 |
| Learned−Value | 180 | -0.511472638980967 | [-0.5385503136194323, -0.4831265616824756] | 负 | 未完成 |

两组共 360 配对行，均采用 18 工况等权、工况内配对的分层 bootstrap（10000 次）。canonical 审计确认配对无缺失，各工况 n=10，两组各工况 CI 上界均小于 0。区间属于 `pointwise_intervals_no_familywise_claim`，不作 familywise 显著性声明。表中差值单位为 rate，不是百分比相对提升；发布门禁 pending 不改变负统计方向。

## 材料与答辩边界

| 允许使用的口径 | 禁止使用的口径／操作 |
|---|---|
| 如实展示已执行的合成域正式负结果、全 idle 和零回退；同时展示“统计结论：负”和“发布状态：复核中”。 | 宣称 AI 战胜基线、Learned 优越或已正式发布完成；用 pending 掩盖负统计结果。 |
| 讨论失败检测、冻结证据追溯、发布治理、确定性约束层、协议仿真与交互沙盒的工程价值。 | 宣称真实卫星、真实轨道、真实 6G 收益或泛化能力；以零违规证明实际部署效果。 |
| 将小样本拟合与域偏移列为解释假设，明确因果证据有限。 | 将 all-idle 归为加载故障、Guard 回退、模型缺失，或证明所有学习方法失败。 |
| 将后续研究与本批冻结结果严格区分，保留原始字节与负结果。 | 把 Hybrid 当作本批正式策略；训练或启用 Hybrid/mix recovery pilot；替换为重训模型；手工修改原始 summary、冻结模型、输入或 B/C 证据。 |

## B 交接与发布门禁

1. B 消费本 A 记录、上表 Task 1 canonical JSON 与 C 指定提交的复核记录，核对 ZIP／summary／冻结模型和输入绑定仍一致；A/C 记录必须指向同一批对象。
2. B 按既有门禁生成一个**单独的统一发布对象**，绑定 A/C 裁决与全部不可变对象 hash，并测试缺少复核、绑定不符、错误收益宣称及状态不一致时无法发布；检查通过后才由 B 的发布流程处理新对象的发布状态。
3. 保留原始 summary 的 `result_signoff=pending` 与 `formal_verdict=未完成`，保留原始证据字节；本 A 记录及机器审计均不自行翻转这些字段，不授权手工改写原始 summary。
4. 不得重跑 540 次正式实验。B 只消费既有证据、进行发布对象生成与门禁测试；不得改动 B/C 证据、冻结输入或模型，不训练或启用 Hybrid/mix recovery pilot，不用新模型替换本批结果。
5. 对外材料沿用上述允许／禁止口径，持续保留两组负比较、三策略指标和适用域限制。B 统一发布对象及其测试仍是后续交接动作，本记录不声称已完成。

复核范围签署：A 正式结果复核；依据为本记录列明的 canonical 审计与冻结直接证据，裁决仅在上述绑定和限制内有效。
