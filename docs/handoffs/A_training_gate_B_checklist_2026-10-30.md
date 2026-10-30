# A 样本与切分交接：B 主验清单

验收窗口：2026-10-31 上午（UTC+08:00）；训练交付截止沿用 11/02 22:00。当前状态 awaiting_delivery；本清单不构成训练许可或已验收记录。

请在 A 分支提交 handoff，明确固定 SHA 和以下产物路径（路径可自行安排，交接中给出映射）：

| 输入 | B 的验收条件 |
|---|---|
| H02 回执 | 记录 solve_teacher 独立调用、教师版本、预算、状态、gap 和一条实际标签 |
| 教师样本 JSONL | 09 第15.2节全部字段齐全；唯一 sample_id、scenario_id、Observation、完整候选与唯一 idle；分数尺度见 dataset_card |
| dataset_manifest / dataset_card | 20场景扩样，逐场景状态数（最多4）、种子、成功/失败/超时/不支持/剔除计数、CPU总耗时、输入与产物哈希；全零标签留存 |
| split_manifest | train/validation/calibration/test 名单、原始轨迹/run_id/派生状态映射；同轨迹来源不跨集合；记录划分 seed 和规则 |
| 特征与 mask | 字段顺序、单位、缺失规则、候选映射；不得含真实未来任务、真实信道值或环境能量真值；缺 RUL 不作有效0 |
| normalization | 只由训练集拟合的可审计来源；验证/校准/测试不得反向进入拟合 |

B 将复算哈希、逐行校验合同、检查集合来源交集并独立重生成一条支持范围内标签。当前首版教师训练准入仅 OPTIMAL；非零预测损失为 UNSUPPORTED_LOSS，须如实限定训练范围。B 原先20个初始状态预跑不能替代 A 的20场景扩样。

产出位置：`docs/acceptance/A_samples_split_B_2026-10-31.md` 与 `docs/evidence/B/A_samples_split_2026-10-31/`。未交付不预签，未通过列具体反例。11/02 H05 冻结须另核模型包、测试名单、seed、优化子集与 SHA；本轮通过也不代表模型性能验收。
