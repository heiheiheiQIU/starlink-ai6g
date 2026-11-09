# B交互仿真交付·C独立审计回执（2026-11-09）

## 裁定

**accepted_with_notes**。接受 `codex/b-sandbox-delivery-20261109@c43978cf57694369651a12cfaaa8c5e04cc570c3` 的场景轴编译、参数校验、任务接口、真实事件分页、配置/哈希导出、黄金场景证据与离线源码包，允许C端按冻结合同接入。该裁定不等于正式实验完成，不授权发布策略优越性，也不授权绕过候选输入三方复核、正式冻结或540次正式运行签核。

## 逐项独立证据

| 检查项 | C复核结果 | 裁定 |
|---|---|---|
| 远端身份 | 分支HEAD为 `c43978cf57694369651a12cfaaa8c5e04cc570c3`；功能提交 `3bd22a3`，并发修复 `3f09926`，证据源码版本 `71c40b0`。 | 一致 |
| 本地交接单 | `tmp/B_sandbox_delivery_2026-11-09.md` 与仓库 `docs/handoffs/B_sandbox_delivery_2026-11-09.md` 的Git blob一致。 | 一致 |
| 离线包成员 | 解压包共52个文件；`SHA256SUMS.json`登记的51个成员逐文件重算均一致。 | 一致 |
| 离线依赖 | 16项锁定依赖可从包内wheelhouse安装至干净target；`fastapi`及sandbox模块导入成功。 | 一致 |
| 新鲜黄金运行 | C从离线源码重新执行 `scripts.verify_sandbox`，S1/S2/S3、health_control、S3_repeat共5次完成；运行中可见已完成策略事件批次。 | 一致 |
| 真实结果 | S1 EDF=1、Learned=0；S2 EDF=0、Learned=0；S3 EDF=1、Learned=0；负结果原样保留。S3含ACK丢失、超时、重复块与fallback。 | 一致 |
| 确定性 | S3同seed重复运行的语义事件一致；事件按policy批次发布，各策略仿真时钟独立从0开始。 | 一致 |
| 核心后端复跑 | C在隔离Python中复跑18个API/sandbox/formal/learned/协议核心文件：`279 passed, 1 skipped`；跳过项仅Linux僵尸进程检查。 | 通过；与B所述283的具体收集集合相差4项，不能宣称计数完全复现 |
| 扩大全库复跑 | 排除缺少依赖的PyTorch训练测试和Word格式测试后：`679 passed, 1 skipped, 7 failed, 20 errors`。异常全部来自旧寿命资产路径解析失败或相关Torch缺失，不落在本次sandbox核心交付。 | sandbox无新增回归；全库不能表述为全绿 |
| C前端合同 | 浏览器仅提交 `kind=sandbox_axes`、`compiler_version=sandbox-axis-v1`、8项axes、策略与seed；不在浏览器构造任务/窗口/信道。 | 已接入并由前端测试约束 |
| C前端回归 | 全量前端 `31` 个测试文件、`102` 项测试通过；TypeScript静态检查和Vite生产构建通过。 | 通过 |

## 必须保留的边界

1. 当前黄金场景全部是 `synthetic/sandbox`，仅证明接口、约束、事件链和工程可操作性，不替代正式域外评估。
2. Learned在现有演示工况选择idle且结果为0，页面必须标成实测负结果，不得使用“AI增益”“优于基线”等措辞。
3. B原离线包的前端早于C新版控件；最终提交前必须由C重建最终离线包并在另一台电脑验收。
4. C原始生成前回执已逐字节镜像到 `docs/evidence/B/sprint_2026-11-09/generation/C.json`。三签现在只授权生成180条候选输入；候选清单三方签核、正式冻结与540次运行仍未授权。

## C接入结论

C端采用同一个全局run控制器完成参数提交、在线状态、事件、结果和ZIP导出；事件回放先按 `policy_id` 分流，再按各自 `sim_time_s` 构帧，避免把不同策略的局部时钟错误拼接。参数改变后旧结果明确标记为历史结果。该实现达到“参数变化→后端真实重跑→结果与事件随运行变化”的交互沙盒目标，不再只是固定演示动画。
