# B-N4：learned 评分器接入 Runner 和五接口方案

状态：draft_for_A_C_review；本次是方案交付，不表示已实现learned运行。

## A/B/C 分工与前置交付

A交 `backend/policies/learned.py` 的 `score_actions(observation, *, config=None)`、冻结权重与SHA、policy-features-v1字段顺序、训练集拟合的归一化参数、模型版本、三种子选择依据、model_card和成功/缺RUL/非法输入/失败样例。输入仅公开Observation，返回完整变长CandidateScore列表。B维护Runner、Guard、API工作进程和产物；C展示真实响应和失败/回退原因。

A需确认上一接口稿四项：特征顺序/单位/缺失规则、动作顺序/mask、标签准入与损失尺度、推理入口与预算。数据v2签收不代替该确认。建议初始推理预算100ms（沿用现有网关默认值），在A实测及双方确认后冻结；模型加载耗时单独记录，不混入纯前向延迟。

## 触发到结果

1. 服务验证请求，固定输入文件/seed/环境轨迹，验证模型SHA与特征版本；edf/value保持可运行。显式请求learned但模型包缺失/哈希错误时，提交返回受控422并说明配置不可用；运行中模型故障按下述回退，不伪称模型成功。
2. 每次决策从公开Observation编码；A按candidate_keys输出每个可见任务robust/fast及唯一idle。B新增完整键集合检查，校验有限score、重复/未知task和缺候选；当前公共校验并不强制完整候选。
3. 结构mask之后交统一Guard做链路、功耗、能源和协议约束。现有同块重传锁继续生效，learned不能绕过控制器的retry_required语义。
4. 异常、NaN、超时、非法候选或结构上无有效发送动作时使用约定EDF回退路径；idle可作为合法选择，不把正常idle一律记为失败。EDF回退仍过Guard；无物理合法发送动作时留在idle并记录约束原因。

## 五接口兼容与需要三方确认的差异

| 现有接口 | 接入后的约定 |
|---|---|
| POST /runs | 允许learned；保持旧edf/value请求有效；三策略比较请求需调整当前RunRequest.policy_ids最多2项的公共限制，不能默改 |
| GET /runs/{id} | 沿用queued/running/completed/failed，active_policies展示learned；模型局部回退不等于整个运行failed |
| GET /runs/{id}/events | 沿用分页和事件ID；decision数据展示评分、选中动作、模型/策略版本、延迟及回退原因；C按既有可空/原因语义消费 |
| GET /runs/{id}/results | 各策略模型哈希分别记录；混合规则/模型运行的顶层model_hash按现有规则为null，各by_policy保留真实模型SHA |
| GET /runs/{id}/export | 包含各子运行及模型元信息清单，不把权重二进制塞入ZIP；导出前复核路径、完整性及哈希 |

优先复用现有字段：Decision/事件承载候选评分、版本和原因，by_policy承载模型哈希；manifest记录特征/归一化/模型版本及文件SHA、加载耗时和延迟统计。任何冻结合同/schema/TypeScript镜像变化，先形成差异表，经A/B/C确认后实现。请求模型路径只接受服务端受控配置，不允许客户端任意本机路径。

## 超时、隔离和恢复

目前ScorerGateway使用daemon线程，仅限制等待和并发，无法终止超时推理；而RunService创建的run worker本身为daemon进程，不能再创建multiprocessing子进程。因此本方案选择由服务层直接托管每个run的专用推理进程，与run worker作为同级、受监督的进程，通过有界IPC通信，不在daemon worker内spawn。

服务为每个run登记运行/推理进程及通信句柄；推理超时后停止对应推理进程、丢弃迟到结果，按EDF继续，是否重启及冷启动预算按冻结配置执行。正常完成、run超时、失败和服务close都必须对该run的全部已登记进程执行停止、限时join、必要时terminate/kill和句柄关闭；不能只terminate(run)。Windows部署用带kill-on-close的Job Object或等价受监督进程组兜底服务异常退出，需补进程回收实测后再验收；禁止无限创建线程/进程。

推理超时与整个run超时分开记录；整个run超时沿用failed/partial/恢复流程，不发布正式results。服务刷新/重启按原status和产物恢复，不能把旧评分应用于新Observation。每次评分绑定run_id、决策序号及Observation摘要。

## 验收与后续实验

- 真实冻结权重独立推理；变长任务、idle、robust/fast、缺RUL及完整mask映射。
- 异常/NaN/重复/遗漏候选/超时的受控回退；不复用迟到结果，不泄漏进程。
- 同场景edf/value/learned的任务、信道、能源输入哈希一致；分页无重漏、ZIP一致、故障与刷新恢复正确。
- TestClient回归与真实uvicorn HTTP分别保留证据，再由C做页面消费验收。
- 11/02—03首轮三策略同场景验证后，11/04按冻结18×10矩阵开展正式实验与G4裁决表。成熟优化器尚未交付，不能把当前有限树教师改称可扩展优化器；离线教师仅在共同支持域作参考，算法/预算及缺口单列。

本方案先提交供A/C对齐；尚未修改公共合同、实现learned、执行AI正式实验或生成模型性能结论。
