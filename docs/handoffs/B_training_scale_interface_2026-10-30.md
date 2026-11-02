# B → A：训练扩样与公共接口对齐稿

状态：proposed，依据 B 当前代码核查，不代表 A 已确认或新数据已冻结。

## 可复用接口

- 输入：冻结 `Observation`，含 run_id、policy_id、sim_time_s、tasks、forecast_windows、health、inflight、cache_bytes、forecast_version。
- A 学习评分器输出沿用 `CandidateScore(task_id, mode, score)`，候选键为 task_id/mode；每个任务 robust/fast 加唯一 `(null, idle)`，不依赖固定候选长度。索引顺序必须由特征版本明确，并保存键到行号映射。
- B 标签接口：`solve_teacher(obs, budget_ms)`；`TeacherResult` 含 candidate_scores、solver_status、gap、elapsed_ms；逐条通过 `validate_teacher_result` 验证。
- mask 及可行性由公开输入和统一 Guard 规则确定；不把 UNSUPPORTED 返回的仅 idle 当作其他动作不合法的训练标注。
- 缺 RUL 保持 null 和缺失指示；A 定义特征顺序、单位、缺失填充与归一化，并只在训练集合拟合。B 复核源字段的可用时刻及防泄漏边界。
- 学习评分与安全解码分离；推理异常、超时、非有限分数按网关/Guard 约定回退并记录原因。当前合同校验检查键唯一、唯一 idle 与可见任务引用，不强制每任务 robust/fast 齐全；候选完整性检查及其回退是 learned 接入时需新增并验证的要求。最终接口以 A 新候选和双方 handoff 对齐结果为准。

## 扩样矩阵与支持域

| 维度 | 代表覆盖 | 约束/用途 |
|---|---|---|
| 任务密度 | 单任务、期限冲突、多任务 | 当前教师最多12任务，先测分支爆炸与超时 |
| 优先级 | 均匀、少数关键任务、冲突权重 | 关键任务阈值写入配置 |
| 窗口 | 即时、延迟、短窗口、无窗口 | 最多前三预测窗口，训练场景遵守支持域 |
| 链路速率 | 足够、边界、不足 | fast/robust 均覆盖 |
| 能源与健康 | 正常、reserve边界、低电量、缺RUL | 训练只取公开估计与下界 |
| 丢包/ACK丢失 | 无损、恶化、重传 | 当前非零预测损失及inflight不支持；先留作评估，单列覆盖缺口 |

训练扩样不得为了凑数量绕过 UNSUPPORTED_* 或将非最优标签改为 OPTIMAL。完整状态数、失败/超时/不支持、全零标签、CPU及壁钟成本都保留。

建议先用代表组合做小批计时，按 A 模型需求、支持域覆盖和剩余 CPU 预算确定扩样数量。原有20初始状态只作入口预检。每场景多个状态必须由真实演进采样，保存来源轨迹和采样时刻，不能复制20初始状态冒充扩样。

## 数据和公平性记录

拟统一记录 sample_id、scenario_id、run_id/trajectory_id、采样时刻、environment_seed、完整公开 Observation、候选标签、teacher_version、label_version、feature_version、forecast_version、预算、状态、gap及源配置/产物SHA-256。字段命名先与 A 候选对齐，保持现有公共合同不变。

按场景/原始轨迹先划分再派生状态，同源样本不得跨 train/validation/test；健康校准集与 A-N2 单独处理。为各策略冻结相同任务、信道轨迹及能源输入文件与哈希，不能仅凭相同 seed 推断环境相同。

## 对齐后才冻结的事项

1. A 交付的真实样本格式、特征顺序/单位/缺失规则、动作顺序和 mask 定义。
2. 训练与验证准入状态、损失函数和教师分数尺度；是否需要扩展当前教师支持域。
3. 数据量、场景比例、各来源归属和种子列表；训练/验证/测试及健康校准的分开边界。
4. 模型包推理入口、推理预算、超时/NaN/无合法动作的回退约定与日志位置。

B 的生成器和 A 的训练器按上述确认结果衔接；不在尚未取得 A 固定交付时制造另一套不兼容数据格式。
