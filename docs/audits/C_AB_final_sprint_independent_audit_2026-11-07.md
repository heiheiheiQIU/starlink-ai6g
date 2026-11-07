# A/B 最终冲刺独立审计（C）— 2026-11-07

## 1. 审计对象与结论

- A 分支：`codex/a-final-sprint-review-20261107`，远端提交 `c3da9234cfd229bc81241a89e8e3a5ee54f5d450`；
- B 分支：`codex/b-final-sprint-review-20261107`，远端提交 `58c68b6dc1f7fd658cf87c7796649798f113ffa9`；
- 审计方式：仅 fetch 与 detached worktree 复核，未合并、未生成正式输入、未运行正式策略。

**总裁定：A 线事实裁定接受；B 线工程交付为 `changes_requested`。A 提出的两项阻断成立，正式输入生成必须继续保持 0 条，A/B/C 预生成回执不得签为 accepted。**

当前允许状态：`claim-A1`、`claim-X1/X2/X3` 全部保持 `pending`；A-N4b 保持 `blocked_diagnostics_verified`；旧冻结模型保持不变。

## 2. 事实交叉复核

| 事实 | 复核结果 | 证据 |
|---|---|---|
| A、B 远端完整 SHA 可获取 | 一致 | 两个远端引用分别解析到 `c3da923…`、`58c68b6…` |
| B 分支包含 A 最新提交 | 一致 | `c3da923…` 是 B HEAD 的祖先 |
| B 分支包含原三问题修复 `03cbb22…` | 一致 | `03cbb22…` 是 B HEAD 的祖先 |
| A-N4b 不可训练、不可替换旧模型 | 一致 | `docs/acceptance/A_N4b_final_ruling_A_2026-11-07.md` |
| A-N4b 有效状态8、idle最优集合7/8、唯一非idle最优0/8 | 一致 | 同上，且 `claim-A1` 未签核 |
| 预登记 formal_v2 种子为600000—600179，共180条 | 一致 | `experiments/formal_v2/registration.json` 与 `generation/subject.json` |
| 旧180条已退出正式评价 | 一致 | `experiments/engineering_regression_v1/README.md` 与 `backend/formal_freeze.py` 的 population gate |
| 当前正式输入0条、正式运行0次 | 一致 | `docs/evidence/B/formal_v2_review_2026-11-07/review_index.json` |
| B 记录701 passed、1 skipped；前端77项；图件合同4项 | 日志可验证 | `docs/evidence/B/formal_v2_review_2026-11-07/final.log`、`frontend.log`、`figures.log`；C独立复跑图件合同4/4通过 |
| 生成前A/B/C回执均为pending | 一致 | `docs/evidence/B/formal_v2_review_2026-11-07/generation/A.json`、`B.json`、`C.json` |

说明：本机当前隔离审计环境没有 B 日志使用的冻结 Python 依赖，故没有声称重新跑出701项；本审计核对了原始日志、SHA清单、提交可达性，并独立复跑无需额外依赖的图件合同4项。

## 3. 阻断项

### P0-1：生成后泄漏核查脚本未进入冻结代码哈希

`backend/formal_freeze.py::source_hashes()`仅覆盖 `backend/**/*.py`、`training/*.py` 与 `experiments/analyze_formal.py`，不包含 `scripts/prepare_formal_v2_review.py`。而该脚本负责生成后来源隔离、泄漏证据和A/B/C输入回执模板。当前脚本 SHA256 为 `6c9d2d41…e9ac`，但替换其字节不会改变预生成 `subject.code_sha256`。

风险：三方签核的“生成后核查方法”可在不触发预生成冻结对象变化的情况下被替换，破坏签核对象闭包。

**修复要求：**把该脚本纳入权威 `source_hashes()`；新增回归测试，先生成预签对象，再篡改脚本，必须导致回执或生成门禁拒绝。

### P0-2：两份数据划分文件未绑定预生成签核对象

`generation/subject.json::source_inputs`当前只有三项：A-N4b sources、旧教师 sources 与开发矩阵；缺少：

- `data/teacher/a_n3_20_v2/splits.json`，SHA256 `88267328…d1f8`；
- `data/teacher/a_n4_pilot_v1/source_splits.json`，SHA256 `aaa5c558…e95`。

更严重的是，`scripts/prepare_formal_v2_review.py`只复制 A-N4b 的 `source_splits.json`，并未复制旧教师 `a_n3_20_v2/splits.json`，但方法说明又要求A复核“来源和训练划分”。因此当前证据包不能完整支持这项复核。

**修复要求：**两份划分文件同时进入预生成 `subject.source_inputs`，也同时复制进生成后 `leakage.source_files`；任一文件在签核后被修改，生成、索引或冻结至少一道门必须拒绝。

## 4. 非阻断但必须同步修正

1. `docs/report/report_v2.md`中的“已启动/重建进行中”更新为：“数据重建试点完成，训练门禁未通过；A-N4b仅作为阻塞诊断，未替换旧冻结模型。”
2. 删除或暂不写“后端570项、前端71项”；测试数量必须在最终集成提交上重跑并单独签核，不能复用其他分支计数，也不能由 `claim-E2` 支撑。
3. “可在干净环境完整复现”降为“已提供复现清单，换机验收待完成”。
4. C-F03 在进入报告/PPT前必须把“AI决定”改成“AI参与价值排序”，把“丢失”改成“预测丢失”，把回箭头限定为“离线评估/后续版本迭代；当前不在线更新模型”。
5. 当前正式材料不得使用未签收的整包图件状态；A图仅为 `review_pending`，C-F03 为 `changes_requested`。

## 5. B 修复后的复验门槛

1. `subject.source_inputs`包含上述两份划分文件；`source_hashes()`包含泄漏核查脚本；
2. 新增至少三项篡改拒绝测试：核查脚本、旧教师splits、A-N4b source_splits；
3. 重生成 pending 的 A/B/C 预生成模板，旧模板全部作废，不得手工沿用；
4. A复核来源/划分，B复核生成与统计对象，C复核180条清单、三策略共享输入及全部SHA；三者分别签署；
5. 完成上述步骤前：正式输入=0、正式运行=0、四档结论=“未完成”。

## 6. C 当前决定

- 不签 `generation/C.json`；
- 不运行 `backend.formal_v2 --receipts`；
- 不合并 A/B 分支到当前前端/材料工作树；
- 报告继续补全，但同步采用 A 的事实口径并暂缓使用 C-F03，直至修图通过复核。
