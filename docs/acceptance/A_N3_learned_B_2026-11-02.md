# A-N3 learned 修复版 B 独立复验

日期：2026-11-02（Asia/Hong_Kong）。结论：**accepted_with_notes**，替代 11/01 对旧候选的 changes_requested；旧失败证据保留。

验收对象：PR #8，`1c90246376b91fb789154b22530b25bab2142b7e`。仅签收 **learned 小样本冻结包与评分/回退接口行为**；不表示 Runner/API 已接入、已合 main 或算法效果通过。

## B 本轮实际结果

| 检查 | B 实测 |
|---|---|
| 原接收人坏 ZIP 回归 | 1 passed；旧版为 1 failed，新版受控返回 MODEL_FORMAT |
| 数据/训练/learned/runner/API/read-retry 组合定向 | 48 passed，1 条既有弃用警告；含 A 新增坏 ZIP、截断 NPZ 两例 |
| 固定候选全库 | 503 passed，1 条同类警告，26.17 s |
| 模型身份 | 五文件、运行/训练配置与旧候选逐字节一致；manifest、八个 float32 有限数组和 API 补丁身份通过 |
| 正常评分 | 20 条冻结观测完整候选、唯一 idle、有限评分、输入不变；inflight mask=-1、空任务 idle 通过 |
| 数据和选择 | 独立重算 train-only 归一化；validation 选 seed=20261033 与记录一致 |
| 故障 | 缺文件、错哈希、坏格式、NaN、非法输入受控；网关异常/超时分别 EDF 回退 MODEL_UNAVAILABLE/MODEL_TIMEOUT |
| 本机延迟 | 冷加载首评分 2.4061 ms；1000 次 warm 中位数 0.4813 ms、p95 0.6283 ms、最大 1.1637 ms |

证据：`docs/evidence/B/A_N3_learned_recheck_2026-11-02/`，命令和环境见 README.md，哈希见 files_sha256.json。源码通过 git archive 固定；未改 A 实现、权重、训练或测试样本。

## 修复判断及边界

`_load_bundle` 新增捕获 `zipfile.BadZipFile`、`EOFError` 并映射为 MODEL_FORMAT，关闭 B 原阻塞。坏 ZIP/截断 NPZ 已实际运行；没有单独制造 EOFError 的独立测试，不将代码覆盖推断成另一项实测。

仍是 20 条 synthetic 初始观测（12/4/4），不能据此声称泛化或优于规则策略。test 仅在选模后执行的源码控制流/冻结记录已审，历史执行次数不能由产物独立证明。网关测试验证等待超时和回退，不证明生产推理进程隔离/强制终止已实现。

下一步 B 可启动 learned 接入；A 无需因本缺陷重训或再次改权重。R2/R5 回执已从独立分支取得，合并准备见 `docs/handoffs/B_progress_and_next_2026-11-02.md`。
