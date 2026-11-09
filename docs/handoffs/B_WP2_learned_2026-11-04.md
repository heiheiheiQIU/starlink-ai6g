# B WP2：learned 运行与五接口交接

日期：2026-11-04（UTC+8）。状态：ready_for_review；在B接续候选0638428基础上实现，未修改共享main。冻结A模型、数据与推理实现保持原样；本次不是重训或正式收益实验。

## 交付行为

- CLI/Runner与POST /runs支持edf、value、learned。每请求仍最多两策略；三策略用同环境的配对请求完成，不修改合同/Schema/前端镜像。
- learned通过A的score_actions评分，再经完整候选校验与现有Guard；遗漏、重复、未知任务、NaN等INVALID_SCORE回退EDF。
- 正常主动idle、空队列idle保留为合法选择；有任务但全部发送候选被结构mask限制时，明确NO_VALID_CANDIDATE回退，不计为模型成功。
- 同块重传控制器继续优先执行公开事件推导的义务；decision保留模型原始评分，以RETRY_REQUIRED解释动作覆盖，manifest另计retry_override_count。
- 缺失/损坏模型在创建run前受控422，details.reason=MODEL_UNAVAILABLE；运行中推理异常、退出或超时回退EDF并保留原因。模型局部回退不使整个run伪失败，运行级失败不发布正式结果。

## 推理隔离和生命周期

服务层托管运行worker和推理进程作为同级进程；没有在daemon worker内部创建子进程。推理队列容量为1，调用绑定run_id、决策序号及Observation摘要，迟到或身份不匹配的响应不能进入新决策。

暖评分预算100ms，模型在子进程加载完成后才接收决策；加载时间单列cold_load_ms，不混作纯前向时间。超时后停止复用该推理通道，本run后续回退EDF；不反复拉起进程。服务监督循环回收超时推理；CLI独立运行由Runner持有同一监督器并在finally回收。

Windows使用kill-on-close Job Object，并在子进程执行前设置启动gate。子进程等待gate时检查父进程存活，覆盖“spawn已发生、尚未加入Job”时父进程退出的窗口；这两条启动路径都有真实强杀回归。正常完成、run超时、worker崩溃、close、服务强杀均覆盖运行及推理进程。

状态文件持续分享锁或损坏JSON时，监控线程继续监督后续运行；当前run标为STATUS_UNAVAILABLE失败并回收进程。close即使读取状态失败也执行资源清理。Linux加入父死信号及僵尸状态判别，但本机Windows上的Linux专用回归跳过，不声称Linux已实测。

## 五接口、身份与导出

- 状态接口沿用queued/running/completed/failed，事件沿用冻结DecisionData与分页格式，result和ZIP沿用旧接口。
- 独立learned结果的顶层及by_policy.model_hash均为冻结权重SHA；混合规则与learned时顶层为null、子策略分别记录真实SHA或null。
- B固定已签收manifest SHA=949370f65165437a95b5858b23103b6cac892913592d1a4b54a3d3d4d27445a8。先以同一份bytes校验和解析manifest，再验证其schema/version、四个引用产物、权重/归一化配置和数组格式。未来模型版本需显式更新服务端可信登记，不接受客户端任意模型路径。
- 启动时固定验证过的模型配置快照，子进程不会重新读取可能已变的配置文件。manifest包含五文件SHA、特征/归一化版本与运行诊断。
- 决策次数、回退原因、成功模型决策、重传覆盖、加载耗时放manifest.inference；不回写已哈希的config。model_hash表示本run配置的模型身份，实际使用/回退以事件及统计判断。
- ZIP先把允许的文件读成快照，核对根/子manifest的完整文件集合及每项SHA，再用同一批bytes打包。产物或manifest损坏受控500，不返回带旧摘要的ZIP；模型权重本体不放ZIP。

## 验证与证据

实际运行源码提交：`5411fefa5f91b10ecc40b1203347a6fa7159334b`。最终全库552 passed、1项Linux专属skipped、1条既有警告；前端61项及类型/构建通过。

完整用例、红绿记录及真实HTTP见[WP2证据](../evidence/B/WP2_learned_2026-11-04/README.md)。公共合同、Schema、前端源码/锁、A模型/训练数据与基线逐字节核对；只对原“learned是非法策略”的测试改为未知策略测试。

首轮开发比较用同一冻结任务/信道/能源输入的edf/value与edf/learned两请求；重复EDF不计额外独立样本。结果只证明运行与可比性链路，不代表540次正式实验或模型有效。

独立审阅提出的六项重要问题已加入失败回归并修复；Linux专用回归留作平台限制。缺模型HTTP诊断问题按交接可诊断性要求一并修复。接收人A/C尚需对新候选复测，不能用本回归代签。

## A/C 接收与下一项

- A继续按B_teacher_support_2026-11-04.md做新版本小批生成/审计；WP2使用已冻结旧模型，未阻塞等待新训练。新模型替换需要重新验包和登记。
- C现在可通过API客户端实际提交learned或规则/learned配对，消费模型版本、原始评分、动作、回退原因和ZIP。页面真实创建与视觉交互仍由C联调；新增结构mask回退理由为普通原因字符串，合同结构未变。
- B在接收回执后继续开发场景覆盖、模型适用域与正式实验冻结。18×10、强优化器、统计签核仍未完成；未输出AI收益或现实卫星结论。
