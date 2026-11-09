# C侧Formal-v2候选输入审核准备回执

日期：2026-11-09

状态：`ready_waiting_for_B_candidate_package`

## 已完成

1. 确认 `docs/evidence/B/sprint_2026-11-09/generation/` 中A/B/C三份生成前回执均为 `accepted`；
2. 独立比较三份回执的 `subject`，内容完全一致；
3. 新增 `scripts/review_formal_v2_candidate_c.py`，在B候选包到达后执行既有 `verify_candidate()`，并复核18×10、600000—600179和五类唯一性；
4. 输出固定为 `machine_verified_human_pending` 和 `formal_runs_authorized=false`，不会代替C人工回执；
5. 明确当前C工作树不是已签候选生成环境，B必须回到 `48157a8f...` 对应源码并重算 `code_sha256=88e44ec...`。

## 验证

- 新增审核测试：`7 passed`；
- formal-v2原门禁与新增测试合跑：`14 passed`；
- 扩大全库：`686 passed, 1 skipped, 7 failed, 20 errors`；
- 完整收集另因当前离线环境缺少PyTorch和python-docx出现2项collection error。

扩大全库失败/错误均位于既有寿命资产路径、PyTorch训练/旧资产检查或Word依赖域；本次新增测试和formal-v2门禁全部通过。因此本回执只声明“C候选审核入口就绪”，不声明Python全库全绿。

## 下一步

1. B在精确冻结源码生成180条候选输入；
2. B交付candidate manifest和post-generation来源/泄漏复核包；
3. C运行审核脚本并人工核对来源材料；
4. A/B/C签署候选阶段回执；
5. 三签前不得启动540次正式运行。
