# C对formal_v2实际候选的库存与哈希复核

> 日期：2026-11-09
> 审核对象：`codex/b-formal-handoff-20261109@b4faac9d687c3a5b47db19d06f9e5b72cd185e05`
> 生成代码：`48157a8f4a1cdd7770685b79deb3fe4524b1bf7d`
> 裁定：`accepted_with_notes`
> 运行授权：`false`

## 1. 裁定

C接受本批实际候选的库存、文件哈希、18×10工况均衡、seed范围和三策略共享输入设计。该裁定仅完成C负责的候选清单与哈希侧复核，不代表完成最终泄漏审查，也不授权启动540次正式运行。

正式回执`docs/evidence/B/formal_v2_candidate_2026-11-09/review/C.json`保持`pending`，未被修改。原因是A尚需复核训练来源、数据划分和旧教师观测边界，A/C也尚未共同冻结最终`review/leakage.json`的字节与SHA256。

机器可读回执：`docs/evidence/C/formal_v2_candidate_2026-11-09/C_inventory_hash_review.json`。

## 2. 复核对象

- 候选清单：`docs/evidence/B/formal_v2_candidate_2026-11-09/candidate/manifest.json`；
- 候选协议：`docs/evidence/B/formal_v2_candidate_2026-11-09/candidate/protocol.json`；
- 180份配置：`docs/evidence/B/formal_v2_candidate_2026-11-09/candidate/configs/`；
- 冻结绑定：`docs/evidence/B/formal_v2_candidate_2026-11-09/review/binding.json`；
- 来源副本：`docs/evidence/B/formal_v2_candidate_2026-11-09/review/sources/`；
- 泄漏复核草稿：`docs/evidence/B/formal_v2_candidate_2026-11-09/review/leakage.json`；
- 总哈希索引：`docs/evidence/B/formal_v2_candidate_2026-11-09/SHA256SUMS.json`。

## 3. 实际复核结果

| 检查项 | 实际结果 | 裁定 |
|---|---:|---|
| 候选轨迹 | 180 | 通过 |
| 工况分布 | 18格，每格10条 | 通过 |
| seed | 600000—600179，180个唯一值 | 通过 |
| trajectory_id | 180个唯一值 | 通过 |
| config_path | 180个唯一值 | 通过 |
| config_sha256 | 180个唯一值，逐文件错误0 | 通过 |
| input_hash | 180个唯一值 | 通过 |
| content_hash | 180个唯一值 | 通过 |
| 配置内部seed | 180份全部与manifest一致 | 通过 |
| 信道seed | 180份全部与manifest一致 | 通过 |
| scenario_id | 180份全部与trajectory_id一致 | 通过 |
| 策略污染 | `policy_runtime=null`且`actions=[]`，错误0 | 通过 |
| 正式策略 | 仅EDF、Value、原始Learned | 通过 |
| 计划运行键 | 180×3=540，唯一运行键540 | 通过 |
| 共享输入 | 每条轨迹仅一份配置，三策略复用同一输入 | 通过 |
| 排除seed | 390个，候选交集0 | 通过（库存侧） |
| 排除内容哈希 | 374个，候选交集0 | 通过（库存侧） |
| 来源副本 | 7份，登记哈希错误0 | 通过（字节侧） |
| 总哈希索引 | 204项，缺失0、错误0 | 通过 |
| 已执行正式策略运行 | 0 | 符合当前门禁 |

候选manifest SHA256为：

```text
2b0814db44b7c70cd94e44608e34c762ffaa86969ea6f955e4736b7b3cdcd31f
```

## 4. 明确未签收的内容

以下内容不在本回执的批准范围内：

1. A负责的训练来源和数据划分语义；
2. 旧教师观测缺少完整场景seed时的来源边界解释；
3. 最终`review/leakage.json`字节和SHA256；
4. `review/A.json`、`review/B.json`、`review/C.json`三份正式post-generation回执；
5. 540次正式运行及其任何胜、负、未检出稳定差异或未完成结论；
6. Hybrid、重训练、换模型或改变统计协议。

## 5. 下一门禁

1. A完成来源、划分、旧教师观测边界和实际交集复核；
2. A/C共同确认最终`review/leakage.json`的完整字节；
3. 计算最终leakage SHA256；
4. A/B/C分别在本人正式回执中绑定同一个leakage SHA256；
5. 冻结工具接受三份回执后，B才可以启动正式预跑与540次运行。

在此之前，任何人都不得将C的`accepted_with_notes`改写成“三方已经签收”或“正式运行已经获批”。
