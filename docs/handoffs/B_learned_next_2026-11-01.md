# 11/02 状态更新

本文件的11/01等待状态已由 `B_progress_and_next_2026-11-02.md` 替代：A修复版1c90246经B复验已accepted_with_notes，A R2/R5两份回执已取得；下一步是实际合并和learned五接口接入，不再等待坏ZIP修订。以下保留历史交接内容。

# B接续准备：PR #8已到件，转入learned独立验包

日期：2026-11-01（香港时间）。状态：prepared；静态接收预检通过，功能验收待执行。

## 固定接收版本

- PR #8：https://github.com/heiheiheiQIU/starlink-ai6g/pull/8，Draft，base为codex/a-next，head为codex/a-n3-learned。
- 最终候选：`11c00374d88dbbc5138c7b2c65029317befa989c`；不再用未推送的97124d4作为接收目标。
- A已应用B最小API补丁，应用提交3ea06f6；A接收回执为 `docs/acceptance/B_API_lock_A_2026-11-01.md`。
- B当前源码仍为576eb48；本轮仅同步、隔离接收和准备，未整支合入A，也未合main。

## 已由B独立完成的预检

固定候选导出到 `runs/b_learned_intake_20261101/source/`。模型五文件实际存在，包含weights.npz，无需再向A索取同一批权重。

- 五文件SHA与A冻结verification一致，且原字节与候选Git blob一致；manifest的四个产物引用一致。
- 运行配置SHA为518c447945783600060ab6c404186f9dc2e78f107be317fa9b26b62a448fdee2，训练配置SHA为788e361c5b204c85b232be51482323e66c03442849120c3eafcec57179a7503d，均与A证据及引用一致。
- 用allow_pickle=False读取8个权重数组，键集合、23→32→16及双头形状、float32类型和有限性均通过。
- contracts/schema/v2样本/划分SHA保持冻结；API三个路径与B交付补丁的after SHA逐项一致。
- 复验脚本和结果位于 `docs/evidence/B/A_N3_learned_intake_2026-11-01/`。该预检不导入模型实现、不训练、不运行其功能测试，不构成模型accepted回执。

## 下一次执行顺序

### 1. 先做正式模型验收

在上述固定副本中复验，沿用B解释器和工作区专用临时目录；为legacy测试配置副本内的资产目录联接，保持资产原件不变。无Git副本运行时限定Git搜索上界到该审查目录的父目录，避免把外层B仓库HEAD写成A候选；证据同时记录真实候选SHA和源码哈希。

第一组：`tests/test_policy_dataset.py tests/test_policy_training.py tests/test_learned_policy.py tests/test_policy_runner.py`。随后加 `tests/test_api.py tests/test_api_read_retry.py` 验组合；A报告79/92/501通过只是其历史记录，B按实际用例数与结果记账。

第二组：对20条冻结Observation实际调用score_actions，独立核对完整候选键、唯一idle、有限分数、结构mask=-1.0、输入未变；分别核验缺文件、错哈希、坏格式、NaN、异常及100ms超时回退，正常idle不得误记模型失败。

第三组：复算train-only归一化及12/4/4来源名单，审阅三seed选择和test一次性评估流程；不重新选seed或重训以美化test。独立量测冷加载及warm延迟，明确环境差异。最后对固定组合副本跑全库并保存失败/警告。

输出：`docs/acceptance/A_N3_learned_B_2026-11-01.md`（日期随实际完成时间调整）及完整证据。范围限learned小样本冻结包与接口行为，不能从4个test样本推断泛化或策略优越性。

### 2. 包验收后接入Runner和五接口

以10/31接入方案为基础，先列出A/B各自修改文件差异，按功能接入，避免整支合并带回旧任务板或旧API。保留B当前seed、状态读取和发行版本溯源修复；候选完整性、Guard、重传锁、模型哈希和回退原因都要贯通。

当前请求最多2策略。三方批准合同扩展前，先以相同冻结任务/信道/能源输入的配对请求完成edf/value/learned首轮可比验证；三策略同请求及镜像更新另行评审。进程超时按服务层同级监督设计回收，不在daemon worker内spawn。

验收包含分页、ZIP、刷新/失败恢复、评分展示，以及真实HTTP；TestClient与真实HTTP分别记录。模型推理通过不等于API已接通。

### 3. 两份A回执到达后合R2→R5

C的B1 accepted和A的API补丁接收都已到件。当前远端仍未见A的R2四项手算覆盖确认及R5公平性专门回执；截图明确它们仍在A本地codex/a-r2-r5-receipts，不属于PR #8。继续等待这两份可读取的固定版本回执，不把模型PR当作替代签收。

回执到齐后按PR #3→#4→#5→#6逐层处理base/head、合并结果回归与证据哈希。10/31预合并219/248/293/309不替代新的合并验证。

## 对原计划的状态修正

- “A代码/权重待交付”已解除；“A需接收B补丁”已由其回执确认；不再重复安排这些动作。
- 当前关键路径为：固定11c00374独立验包 → 有限签收 → learned五接口 → 三策略同场景验证。
- 11/02 22:00交付截止沿用现有安排；11/04正式实验仍需模型/运行/优化器与统计门禁，不提前把管线结果写成G4结论。

本轮准备文件在B分支交付；未给PR #8转Ready、合并或预签功能验收。
