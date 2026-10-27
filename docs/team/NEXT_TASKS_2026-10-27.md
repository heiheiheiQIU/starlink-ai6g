# 三人下一阶段任务（2026-10-27起）

原则：B先冻结合同并提供教师/API入口，A和C并行推进各自可独立部分；三人每日只安排一个可验收主任务。状态同步到`docs/task_board.csv`。

## 成员A：健康输入与AI评分

### A-N1 正式健康接口（优先级P0，10月29日22:00前）

- 输入：A1 `LegacyPrediction`边界、B的`HealthEstimate`类型、仿真history/now_s。
- 实现：`backend/health/estimator.py`、`configs/health_observation.json`、`tests/test_health_estimator.py`、`docs/handoffs/H01_health_estimate.md`。
- 要求：没有可靠容量标签时采用明确配置的合成观测误差；RUL不可用为null；available_at防未来泄漏；SOC、容量、能量单位断言完整。
- 交付：成功、RUL缺失、输入错误三份正式`HealthEstimate`样例；调用命令、配置哈希、测试日志。
- 验收人：B主验，C检查字段可展示。完成后H01才可从`accepted_with_notes`升级。

### A-N2 数据隔离与校准（P0，10月30日22:00前）

- 按完整run_id拆训练/校准/测试，输出`split_manifest.json`并断言无交集。
- 校准只用校准集；样本不足时写“场景保守边界”，不得写95%保证。
- 输出无RUL、无不确定性、传统状态估计的开关配置。

### A-N3 教师数据与学习评分器（依赖B-N2，11月2日22:00前）

- 先用B的20场景预跑接口生成标签，保留solver_status、gap、elapsed_ms和版本。
- 实现共享任务MLP＋全局状态特征，`score_actions`只返回评分。
- 测试空队列、候选mask、NaN受控错误、相同输入可复现；先小样本过拟合再三种子训练。
- 交付权重、训练配置、`model_card.md`、CPU/GPU延迟、失败样本和B可直接调用示例。

### A-N4 技术供稿与消融（11月5日20:00前）

- 向C交方法、数据、局限、3—4页答辩原稿；每张图带run_id、命令、单位及可/不可支持结论。
- 消融由B统一evaluate，A不另算分母。

## 成员B：合同、仿真与集成

### B-N1 H00公共合同冻结（P0，10月28日18:00前）

- 评审`docs/contracts/README.md`，实现`backend/contracts.py`和`configs/schema.json`。
- 提供合法/非法fixture及契约测试；A/C书面确认单位、null语义和错误码。
- 提交`docs/handoffs/H00_contract.md`；此任务完成前A/C不得自造公共字段。

### B-N2 最小环境、基线与教师接口（P0，10月30日20:00前）

- 实现队列、窗口、能量、ACK/重传、事件日志、guard、EDF/价值基线及`solve_teacher`。
- 六个共同契约样例全部通过；20场景预跑给出预算、gap、超时和失败样本。
- 交A可独立生成一条标签的命令与fixture。

### B-N3 API与实验骨架（10月31日20:00前）

- 实现五个HTTP端点、run目录、事件分页和统一错误体。
- 给C completed、running、failed三类fixture；fixture永久标识非实验结果。
- API失败不得静默返回成功数据；results未完成返回409。

### B-N4 A/B集成与统一评价（11月4日20:00前）

- 接入A正式HealthEstimate和score_actions；模型异常记录fallback。
- 实现18工况、基线/本方法/oracle上界统一评价及可复现run导出。
- 11月2日冻结测试集合；11月4日完成收益审查并保留负结果。

## 成员C：前端、证据与材料

### C-N1 前端基线和信息架构（P0，10月28日22:00前）

- 先按`C_DeepSeek超详细执行与验收手册`完成接管报告。
- 建立`frontend/`技术栈基线、两页组件树、状态矩阵及字段到组件映射。
- 输出1920×1080和1366×768静态设计；fixture全局标“契约样例/非实验结果”。

### C-N2 合同镜像与静态高保真（依赖B-N1，10月30日22:00前）

- 镜像`contracts.py`到TypeScript，完成运行驾驶舱、对照实验台和证据抽屉。
- 覆盖loading/empty/queued/running/completed/failed/fallback/history/offline。
- 不从旧截图或DOM计算科学指标。

### C-N3 API联调（依赖B-N3，11月2日20:00前）

- 完成创建run、轮询、事件分页、结果、export闭环。
- 测试刷新恢复、两策略隔离、参数变化使旧结果失效、409/422/429/500。
- 至少抽查三项页面数字与后端结果/export一致。

### C-N4 材料骨架与证据索引（现在开始，11月5日收技术供稿）

- 按官方模板建立报告目录、PPT故事线、视频分镜和`docs/evidence_index.md`。
- 先写结构和已证实事实；收益数字待真实run。
- 11月5日验收A/B正文、图源、图注、run_id和技术签核；不替他们补造结果。

## 每日同步

每天固定15分钟：每人只报昨日产物路径、验证结果、今日唯一主任务、阻塞。阻塞超过半个工作日写handoff/issue；不得在聊天里口头改合同。10月30日前优先打通“合法无AI闭环”，再接AI评分和前端真实联调。
